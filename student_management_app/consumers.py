import json
import base64
import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer

class VideoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass  # Optionally handle disconnect logic

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
            subject_id = data.get("subject_id")
            session_year = data.get("session_year")
            frame_data = data.get("frame")
            if frame_data:
                # Remove data URL header if present
                if ',' in frame_data:
                    _, encoded = frame_data.split(',', 1)
                else:
                    encoded = frame_data

                # Decode the base64 image data to bytes and then to a NumPy array
                img_bytes = base64.b64decode(encoded)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                # Process the frame using OpenCV (e.g., convert to grayscale)
                # processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                processed_frame = frame

                # Encode the processed frame back to JPEG format
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                processed_base64 = base64.b64encode(buffer).decode('utf-8')

                # Send back the processed frame with a data URL header
                await self.send(text_data=json.dumps({
                    "frame": "data:image/jpeg;base64," + processed_base64
                }))
