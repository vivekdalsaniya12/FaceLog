import json
import base64
import cv2
import numpy as np
import face_recognition
import time
import asyncio
import logging
from datetime import date

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

# Import models – make sure these are defined in your app
from student_management_app.models import Subjects, Students, Attendance, AttendanceReport, SessionYearModel

# Configure logging
logger = logging.getLogger("video_consumer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()  # In production, consider a file handler or logging system.
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def detect_faces(frame):
    """
    Downscale the frame to speed up detection, then upscale the face coordinates.
    Uses the CNN model for improved accuracy.
    """
    scale = 0.9  # Scale factor (adjust as needed)
    small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
    
    # Use the 'cnn' model instead of the default 'hog' for better accuracy.
    locations = face_recognition.face_locations(small_frame)
    encodings = face_recognition.face_encodings(small_frame, locations)
    
    # Upscale face coordinates to match the original frame dimensions.
    scaled_locations = [
        (int(top / scale), int(right / scale), int(bottom / scale), int(left / scale))
        for (top, right, bottom, left) in locations
    ]
    return scaled_locations, encodings

# Synchronous helper to store attendance in the database.

@sync_to_async
def store_attendance_in_db(recognized_ids, subject_id, session_year):
    try:
        # Get subject and session objects
        subject = Subjects.objects.get(id=subject_id)
        session_obj = SessionYearModel.objects.get(id=session_year)
        
        # Use today's date for attendance
        today = date.today()
        
        # Get or create the Attendance record for this subject, session, and date.
        attendance, created = Attendance.objects.get_or_create(
            subject_id=subject,
            attendance_date=today,
            session_year_id=session_obj
        )
        
        # Get all students for the session and subject
        all_students = Students.objects.filter(course_id=subject.course_id, session_year_id=session_obj)
        
        # For each student, update the AttendanceReport if it exists,
        # or create a new one if it doesn't, marking absent by default.
        for student in all_students:
            status = student.enrollment_number in recognized_ids
            AttendanceReport.objects.update_or_create(
                student_id=student,
                attendance_id=attendance,
                defaults={'status': status}  # Mark as present if recognized, otherwise absent.
            )
        return True
    except Exception as e:
        logger.exception("Error storing attendance in DB: %s", e)
        return False

# @sync_to_async
# def store_attendance_in_db(recognized_ids, subject_id, session_year):
    try:
        # Get subject and session objects
        subject = Subjects.objects.get(id=subject_id)
        session_obj = SessionYearModel.objects.get(id=session_year)
        
        # Use today's date for attendance
        today = date.today()
        
        # Get or create the Attendance record for this subject, session, and date.
        attendance, created = Attendance.objects.get_or_create(
            subject_id=subject,
            attendance_date=today,
            session_year_id=session_obj
        )
        
        # For each recognized student, update the AttendanceReport if it exists,
        # or create a new one if it doesn't.
        for stud_id in recognized_ids:
            student = Students.objects.get(enrollment_number=stud_id)
            AttendanceReport.objects.update_or_create(
                student_id=student,
                attendance_id=attendance,
                # status=True
                defaults={'status': True}  # Mark as present.
            )
        return True
    except Exception as e:
        logger.exception("Error storing attendance in DB: %s", e)
        return False
    

class VideoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.info("WebSocket connection accepted.")
        self.recognized_face_ids = set()  # Initialize the set to store recognized face IDs
        self.attendance_saved = False  # Flag to ensure we only store attendance once

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        # When the connection is closed, store attendance if not already done
        if not self.attendance_saved and hasattr(self, "subject_id") and hasattr(self, "session_year"):
            if self.recognized_face_ids:
                success = await store_attendance_in_db(
                    list(self.recognized_face_ids),
                    self.subject_id,
                    self.session_year
                )
                if success:
                    logger.info("Attendance stored successfully for IDs: %s", self.recognized_face_ids)
                else:
                    logger.error("Attendance storage failed.")
            self.attendance_saved = True

    async def receive(self, text_data=None, bytes_data=None):
        # Process text messages (initialization or fallback frame data)
        if text_data:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError as e:
                logger.error("JSON decode error: %s", e)
                await self.send(text_data=json.dumps({
                    "status": "error",
                    "message": "Invalid JSON received."
                }))
                return

            # Handle initialization data (subject and session info)
            if "subject_id" in data and "session_year" in data:
                self.subject_id = data["subject_id"]
                self.session_year = data["session_year"]

                start_time = time.time()
                await self.fetch_student_encodings()
                elapsed = time.time() - start_time
                logger.info(f"Fetched student encodings in {elapsed:.2f} seconds.")

                await self.send(text_data=json.dumps({
                    "status": "success",
                    "message": "Student encodings fetched successfully",
                    "students": self.students_qs  # Remove sensitive data in production!
                }))
                return

            # Fallback: if a "frame" property is sent as text (base64 encoded)
            elif "frame" in data:
                await self.process_frame_text(data["frame"])
                return

            else:
                logger.warning("Received unknown message type.")
                await self.send(text_data=json.dumps({
                    "status": "error",
                    "message": "Unknown data format."
                }))
                return

        # Process binary data (preferred method)
        elif bytes_data:
            await self.process_frame_binary(bytes_data)
            return

    async def process_frame_text(self, frame_data):
        """
        Process a frame that was sent as a base64-encoded string.
        """
        try:
            # Remove header if present.
            if ',' in frame_data:
                _, encoded = frame_data.split(',', 1)
            else:
                encoded = frame_data

            img_bytes = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("Decoded frame is None")
            await self.process_frame(frame)
        except Exception as e:
            logger.exception("Error processing frame text:")
            await self.send(text_data=json.dumps({
                "status": "error",
                "message": str(e)
            }))

    async def process_frame_binary(self, img_bytes):
        """
        Process a frame that was sent as binary data.
        """
        try:
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("Decoded frame is None")
            await self.process_frame(frame)
        except Exception as e:
            logger.exception("Error processing frame binary:")
            await self.send(text_data=json.dumps({
                "status": "error",
                "message": str(e)
            }))

    async def process_frame(self, frame):
        try:
            # Initialize frame counter if not present.
            if not hasattr(self, "frame_counter"):
                self.frame_counter = 0
            self.frame_counter += 1

            # Throttle processing: process only every 4th frame.
            if self.frame_counter % 4 != 0:
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
                if not ret:
                    raise ValueError("Failed to encode frame")
                processed_bytes = buffer.tobytes()
                # Send unprocessed frame as binary.
                await self.send(bytes_data=processed_bytes)
                logger.info("Skipped face detection for frame number %s", self.frame_counter)
                return

            # Convert frame from BGR to RGB for face_recognition.
            rgb_frame = frame[:, :, ::-1]

            loop = asyncio.get_running_loop()
            face_locations, face_encodings = await loop.run_in_executor(
                None,
                lambda: detect_faces(rgb_frame)
            )

            recognized_faces = 0
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                name = "unknown"  # Default label.
                color = (0, 0, 255) 
                if hasattr(self, "known_face_encodings") and self.known_face_encodings:
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    min_distance = np.min(face_distances)
                    best_match_index = np.argmin(face_distances)
                    tolerance = 0.4  # Adjust tolerance as needed.
                    if min_distance < tolerance:
                        name = self.known_face_ids[best_match_index]
                        recognized_faces += 1
                        color = (0, 255, 0)

                        # Add the recognized face ID to the set if not already present
                        if name not in self.recognized_face_ids:
                            self.recognized_face_ids.add(name)
        
                # Draw rectangle and label on the original frame.
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                # cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                # two line for add enrollment number in rectatangle----
                # cv2.putText(frame, str(name), (left + 6, bottom - 6),
                #             cv2.FONT_HERSHEY_DUPLEX, 0.3, (255, 255, 255), 1)

                # If two or three faces are recognized, stop further matching.
                if recognized_faces >= 2:
                    break

            # Encode the processed frame as JPEG.
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 99])
            if not ret:
                raise ValueError("Failed to encode processed frame")
            processed_bytes = buffer.tobytes()
            await self.send(bytes_data=processed_bytes)
            logger.info("Processed frame sent to client (frame number %s).", self.frame_counter)
            
            # Optionally, send recognized face IDs back to the client.
            await self.send(text_data=json.dumps({
                "recognized_face_ids": list(self.recognized_face_ids)
            }))
        except Exception as e:
            logger.exception("Error processing frame:")
            await self.send(text_data=json.dumps({
                "status": "error",
                "message": str(e)
            }))

    async def fetch_student_encodings(self):
        loop = asyncio.get_running_loop()
        try:
            # Get subject and associated students.
            subject = await loop.run_in_executor(None, lambda: Subjects.objects.get(id=self.subject_id))
            students = await loop.run_in_executor(
                None,
                lambda: list(Students.objects.filter(
                    session_year_id=self.session_year,
                    course_id=subject.course_id
                ).values("enrollment_number", "face_encoding"))
            )
            self.students_qs = students

            # Process and cache known face encodings.
            self.known_face_encodings = []
            self.known_face_ids = []
            for student in students:
                face_enc = student.get("face_encoding")
                if face_enc is None:
                    continue
                enc = np.array(face_enc, dtype=np.float64)
                if enc.shape == (128,):
                    self.known_face_encodings.append(enc)
                    self.known_face_ids.append(student["enrollment_number"])   #######################################################################
                else:
                    logger.warning("Invalid encoding shape %s for student %s", enc.shape, student["enrollment_number"])

            logger.info("Student encodings fetched and processed.")
        except Exception as e:
            logger.exception("Error fetching student encodings:")
            self.students_qs = []
            self.known_face_encodings = []
            self.known_face_ids = []
            await self.send(text_data=json.dumps({
                "status": "error",
                "message": "Failed to fetch student encodings"
            }))
