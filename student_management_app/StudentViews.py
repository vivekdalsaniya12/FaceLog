from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage #To upload Profile Picture
from django.urls import reverse
import datetime # To Parse input DateTime into Python Date Time Object
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
import os
import json
import face_recognition
import numpy as np
from io import BytesIO
from PIL import Image
from student_management_app.models import CustomUser, Staffs, Courses, Subjects, Students, Attendance, AttendanceReport, LeaveReportStudent, FeedBackStudent, StudentResult


def student_home(request):
    student_obj = Students.objects.get(admin=request.user.id)
    total_attendance = AttendanceReport.objects.filter(student_id=student_obj).count()
    attendance_present = AttendanceReport.objects.filter(student_id=student_obj, status=True).count()
    attendance_absent = AttendanceReport.objects.filter(student_id=student_obj, status=False).count()

    course_obj = Courses.objects.get(id=student_obj.course_id.id)
    total_subjects = Subjects.objects.filter(course_id=course_obj).count()

    subject_name = []
    data_present = []
    data_absent = []
    subject_data = Subjects.objects.filter(course_id=student_obj.course_id)
    for subject in subject_data:
        attendance = Attendance.objects.filter(subject_id=subject.id)
        attendance_present_count = AttendanceReport.objects.filter(attendance_id__in=attendance, status=True, student_id=student_obj.id).count()
        attendance_absent_count = AttendanceReport.objects.filter(attendance_id__in=attendance, status=False, student_id=student_obj.id).count()
        subject_name.append(subject.subject_name)
        data_present.append(attendance_present_count)
        data_absent.append(attendance_absent_count)
    
    context={
        "total_attendance": total_attendance,
        "attendance_present": attendance_present,
        "attendance_absent": attendance_absent,
        "total_subjects": total_subjects,
        "subject_name": subject_name,
        "data_present": data_present,
        "data_absent": data_absent,
        "profilepic":student_obj
    }
    return render(request, "student_template/student_home_template.html", context)


def student_view_attendance(request):
    student = Students.objects.get(admin=request.user.id) # Getting Logged in Student Data
    course = student.course_id # Getting Course Enrolled of LoggedIn Student
    # course = Courses.objects.get(id=student.course_id.id) # Getting Course Enrolled of LoggedIn Student
    subjects = Subjects.objects.filter(course_id=course) # Getting the Subjects of Course Enrolled
    context = {
        "subjects": subjects,
        "profilepic":student
    }
    return render(request, "student_template/student_view_attendance.html", context)


def student_view_attendance_post(request):
    student_obj = Students.objects.get(admin=request.user.id)
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect('student_view_attendance')
    else:
        # Getting all the Input Data
        subject_id = request.POST.get('subject')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Parsing the date data into Python object
        start_date_parse = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_parse = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

        # Getting all the Subject Data based on Selected Subject
        subject_obj = Subjects.objects.get(id=subject_id)
        # Getting Logged In User Data
        user_obj = CustomUser.objects.get(id=request.user.id)
        # Getting Student Data Based on Logged in Data
        stud_obj = Students.objects.get(admin=user_obj)

        # Now Accessing Attendance Data based on the Range of Date Selected and Subject Selected
        attendance = Attendance.objects.filter(attendance_date__range=(start_date_parse, end_date_parse), subject_id=subject_obj)
        # Getting Attendance Report based on the attendance details obtained above
        attendance_reports = AttendanceReport.objects.filter(attendance_id__in=attendance, student_id=stud_obj)

        # for attendance_report in attendance_reports:
        #     print("Date: "+ str(attendance_report.attendance_id.attendance_date), "Status: "+ str(attendance_report.status))

        # messages.success(request, "Attendacne View Success")

        context = {
            "subject_obj": subject_obj,
            "attendance_reports": attendance_reports,
            "profilepic":student_obj
        }

        return render(request, 'student_template/student_attendance_data.html', context)
       

def student_apply_leave(request):
    student_obj = Students.objects.get(admin=request.user.id)
    leave_data = LeaveReportStudent.objects.filter(student_id=student_obj)
    context = {
        "leave_data": leave_data,
        "profilepic":student_obj
    }
    return render(request, 'student_template/student_apply_leave.html', context)


def student_apply_leave_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect('student_apply_leave')
    else:
        leave_date = request.POST.get('leave_date')
        leave_message = request.POST.get('leave_message')

        student_obj = Students.objects.get(admin=request.user.id)
        try:
            leave_report = LeaveReportStudent(student_id=student_obj, leave_date=leave_date, leave_message=leave_message, leave_status=0)
            leave_report.save()
            messages.success(request, "Applied for Leave.")
            return redirect('student_apply_leave')
        except:
            messages.error(request, "Failed to Apply Leave")
            return redirect('student_apply_leave')


def student_feedback(request):
    student_obj = Students.objects.get(admin=request.user.id)
    feedback_data = FeedBackStudent.objects.filter(student_id=student_obj)
    context = {
        "feedback_data": feedback_data,
         "profilepic":student_obj
    }
    return render(request, 'student_template/student_feedback.html', context)


def student_feedback_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method.")
        return redirect('student_feedback')
    else:
        feedback = request.POST.get('feedback_message')
        student_obj = Students.objects.get(admin=request.user.id)

        try:
            add_feedback = FeedBackStudent(student_id=student_obj, feedback=feedback, feedback_reply="")
            add_feedback.save()
            messages.success(request, "Feedback Sent.")
            return redirect('student_feedback')
        except:
            messages.error(request, "Failed to Send Feedback.")
            return redirect('student_feedback')


def student_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    student = Students.objects.get(admin=user)
    student_obj = Students.objects.get(admin=request.user.id)

    context={
        "user": user,
        "student": student,
         "profilepic":student_obj
    }
    return render(request, 'student_template/student_profile.html', context)


def student_profile_update(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method!")
        return redirect('student_profile')
    else:
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        address = request.POST.get('address')

        try:
            customuser = CustomUser.objects.get(id=request.user.id)
            customuser.first_name = first_name
            customuser.last_name = last_name
            if password != None and password != "":
                customuser.set_password(password)
            customuser.save()

            student = Students.objects.get(admin=customuser.id)
            student.address = address
            student.save()
            
            messages.success(request, "Profile Updated Successfully")
            return redirect('student_profile')
        except:
            messages.error(request, "Failed to Update Profile")
            return redirect('student_profile')


def student_view_result(request):
    student = Students.objects.get(admin=request.user.id)
    student_result = StudentResult.objects.filter(student_id=student.id)
    context = {
        "student_result": student_result,
        "profilepic":student
    }
    return render(request, "student_template/student_view_result.html", context)

def camera_view(request):
    return render(request, 'student_template/camera.html')

# Temporary storage for images (stored in RAM)
TEMP_IMAGE_STORAGE = {}

@csrf_exempt
def save_image(request):
    """Receives images, stores in RAM, and processes encodings"""
    student = Students.objects.get(admin=request.user.id)  # Get the logged-in student
    
    if request.method == 'POST':
        try:
            data = request.body.decode('utf-8')
            start_index = data.find('base64,') + len('base64,')
            image_data = data[start_index:]
            
            # Convert base64 data to image (high-quality processing)
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))

            # Ensure image is in RGB format for processing
            image = image.convert("RGB")

            # Store in RAM (Temporary storage)
            if student.id not in TEMP_IMAGE_STORAGE:
                TEMP_IMAGE_STORAGE[student.id] = []
            
            TEMP_IMAGE_STORAGE[student.id].append(image)

            # Limit to 10 images per student
            if len(TEMP_IMAGE_STORAGE[student.id]) > 5:
                TEMP_IMAGE_STORAGE[student.id].pop(0)  # Remove oldest image

            return JsonResponse({'status': 'success', 'message': f'Image {len(TEMP_IMAGE_STORAGE[student.id])} stored temporarily!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
def extract_and_store_encodings(request):
    """Processes all stored images, extracts face encodings, and stores them in the database"""
    student = Students.objects.get(admin=request.user.id)  # Get the logged-in student

    if request.method == "POST":
        try:
            if student.id not in TEMP_IMAGE_STORAGE or len(TEMP_IMAGE_STORAGE[student.id]) < 2:
                return JsonResponse({"error": "At least 2 images required for processing!"}, status=400)

            encodings = []

            for image in TEMP_IMAGE_STORAGE[student.id]:
                # Convert PIL image to numpy array
                np_image = np.array(image)

                # Detect face locations (high-accuracy)
                face_locations = face_recognition.face_locations(np_image, model="cnn")  # Use CNN for better accuracy
                face_encodings = face_recognition.face_encodings(np_image, face_locations)

                if face_encodings:
                    encodings.append(face_encodings[0])  # Store first detected face encoding

            if not encodings:
                return JsonResponse({"error": "No face detected in images!"}, status=400)

            # Compute average encoding (more accuracy)
            avg_encoding = np.mean(encodings, axis=0)

            # Store encoding in database
            student.face_encoding = avg_encoding.tolist()
            student.save()

            # Clear temporary storage after successful encoding
            del TEMP_IMAGE_STORAGE[student.id]

            return JsonResponse({"success": "Face encoding stored successfully!"})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}) 

    return JsonResponse({'error': 'Invalid request method'}, status=400)