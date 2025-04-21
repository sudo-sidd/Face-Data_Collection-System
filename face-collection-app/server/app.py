import os
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import qrcode
from io import BytesIO
import base64
import cv2
import numpy as np
import tempfile
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import torch
from ultralytics import YOLO

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Add path to YOLO model
YOLO_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'yolo/weights/yolo11n-face.pt')

# Check if GPU is available
DEVICE = 'cuda:0' if torch.cuda.is_available() else 'cpu'
print(f"Using device for YOLO: {DEVICE}")

# Thread pool for async processing (5 users per thread)
MAX_WORKERS = 3  # Adjust based on your CPU/GPU resources
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
# Task queue to limit concurrent user processing
task_queue = queue.Queue(maxsize=15)  # 5 users per thread × 3 threads
processing_tasks = {}  # Track task status by session ID

# Face processing functions
def preprocess_face_for_lightcnn(face_img, target_size=(128, 128)):
    """
    Process a face image for LightCNN:
    - Convert to grayscale
    - Resize to target size
    """
    try:
        # Handle empty or invalid images
        if face_img is None or face_img.size == 0:
            print("Warning: Empty face image received")
            return None
            
        # Convert to grayscale
        if len(face_img.shape) == 3:  # Color image
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:  # Already grayscale
            gray = face_img
        
        # Resize to target size
        resized = cv2.resize(gray, target_size, interpolation=cv2.INTER_LANCZOS4)
        
        # Ensure single channel output
        if len(resized.shape) > 2:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            
        return resized
        
    except Exception as e:
        print(f"Error in face preprocessing: {e}")
        return None

def extract_faces_from_video(video_path, output_dir, face_confidence=0.3, face_padding=0.2):
    """Extract faces from video and save preprocessed images using YOLO"""
    # Check if output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize face detector with YOLO
    try:
        face_model = YOLO(YOLO_MODEL_PATH)
        print(f"Loaded YOLO model from {YOLO_MODEL_PATH}")
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        print("Falling back to OpenCV Haar cascade")
        # Fallback to Haar cascade if YOLO model fails to load
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        use_yolo = False
    else:
        use_yolo = True
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return 0
    
    # Get video properties
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video info: {frame_count} frames, {fps} fps, {width}x{height} resolution")
    
    # Initialize counters
    faces_saved = 0
    processed_frames = 0
    
    # Use a lower sample rate to process more frames
    sample_rate = 10  # Process every 5th frame
    frames_per_sample = 5
    
    
    # Process each frame in the video
    for current_frame in range(0, frame_count, sample_rate):
        print(f"Processing frame batch starting at frame {current_frame}")
        
        # Process next frames_per_sample frames
        for i in range(frames_per_sample):
            # Make sure we don't go beyond the end of the video
            if current_frame + i >= frame_count:
                break
            
            # Set position and read frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame + i)
            ret, frame = cap.read()
            if not ret:
                print(f"Failed to read frame {current_frame + i}")
                break
            
            processed_frames += 1
            
            # Detect faces using YOLO or fallback to Haar cascade
            if use_yolo:
                # YOLO face detection
                results = face_model(frame, conf=face_confidence)
                
                # Check detection results
                if len(results) > 0:
                    print(f"YOLO detection on frame {current_frame + i}: {len(results)} results")
                    
                    if hasattr(results[0], 'boxes') and len(results[0].boxes) > 0:
                        print(f"  Found {len(results[0].boxes)} boxes")
                        
                        for j, box in enumerate(results[0].boxes):
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            
                            print(f"  Box {j}: coords={x1},{y1},{x2},{y2}, conf={conf:.2f}")
                            
                            # Skip if below confidence threshold
                            if conf < face_confidence:
                                print(f"  Skipping box {j} - confidence too low")
                                continue
                            
                            # Add padding around face
                            face_width = x2 - x1
                            face_height = y2 - y1
                            pad_x = int(face_width * face_padding)
                            pad_y = int(face_height * face_padding)
                            
                            # Ensure coordinates are within frame boundaries
                            x1 = max(0, x1 - pad_x)
                            y1 = max(0, y1 - pad_y)
                            x2 = min(frame.shape[1], x2 + pad_x)
                            y2 = min(frame.shape[0], y2 + pad_y)
                            
                            # Crop face
                            face = frame[y1:y2, x1:x2]
                            
                            # Skip if face crop is empty
                            if face.size == 0 or face.shape[0] == 0 or face.shape[1] == 0:
                                print(f"  Skipping box {j} - empty crop")
                                continue
                            
                            # Preprocess face
                            processed_face = preprocess_face_for_lightcnn(face)
                            
                            # Create unique filename
                            timestamp = int(time.time() * 1000)
                            filename = f"frame{current_frame+i}_face{j}_{timestamp}.jpg"
                            filepath = os.path.join(output_dir, filename)
                            
                            if processed_face is not None:
                                # Ensure single channel (grayscale)
                                if len(processed_face.shape) > 2:
                                    processed_face = cv2.cvtColor(processed_face, cv2.COLOR_BGR2GRAY)
                                # Double-check the size
                                if processed_face.shape != (128, 128):
                                    processed_face = cv2.resize(processed_face, (128, 128), interpolation=cv2.INTER_LANCZOS4)
                                # Save the image
                                cv2.imwrite(filepath, processed_face)
                                faces_saved += 1
            else:
                # Fallback to Haar cascade detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5, 
                    minSize=(30, 30)
                )
                
                # Process each detected face
                for j, (x, y, w, h) in enumerate(faces):
                    # Add padding around face
                    pad_x = int(w * face_padding)
                    pad_y = int(h * face_padding)
                    
                    # Ensure coordinates are within frame boundaries
                    x1 = max(0, x - pad_x)
                    y1 = max(0, y - pad_y)
                    x2 = min(frame.shape[1], x + w + pad_x)
                    y2 = min(frame.shape[0], y + h + pad_y)
                    
                    # Crop face
                    face = frame[y1:y2, x1:x2]
                    
                    # Skip if face crop is empty
                    if face.size == 0 or face.shape[0] == 0 or face.shape[1] == 0:
                        continue
                    
                    # Preprocess face
                    processed_face = preprocess_face_for_lightcnn(face)
                    
                    # Create unique filename
                    timestamp = int(time.time() * 1000)
                    filename = f"frame{current_frame+i}_face{j}_{timestamp}.jpg"
                    filepath = os.path.join(output_dir, filename)
                    
                    if processed_face is not None:
                        # Ensure single channel (grayscale)
                        if len(processed_face.shape) > 2:
                            processed_face = cv2.cvtColor(processed_face, cv2.COLOR_BGR2GRAY)
                        # Double-check the size
                        if processed_face.shape != (128, 128):
                            processed_face = cv2.resize(processed_face, (128, 128), interpolation=cv2.INTER_LANCZOS4)
                        # Save the image
                        cv2.imwrite(filepath, processed_face)
                        faces_saved += 1
    
    # Close resources
    cap.release()
    
    return faces_saved

# Routes
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/session/start', methods=['POST'])
def start_session():
    data = request.json
    student_id = data.get('studentId')  # Registration Number
    name = data.get('name')
    year = data.get('year')
    dept = data.get('dept')
    
    if not all([student_id, name, year, dept]):
        return jsonify({"error": "All student details are required"}), 400
    
    # Create unique session ID
    session_id = str(uuid.uuid4())
    
    # Create student directory
    student_dir = os.path.join(DATA_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)
    
    # Create faces directory named after registration number (instead of "faces")
    faces_dir = os.path.join(student_dir, student_id)
    os.makedirs(faces_dir, exist_ok=True)
    
    # Create session info
    session_data = {
        "sessionId": session_id,
        "regNo": student_id,
        "name": name,
        "year": year,
        "dept": dept,
        "startTime": datetime.now().isoformat(),
        "videoUploaded": False,
        "facesExtracted": False
    }
    
    with open(os.path.join(student_dir, f"{session_id}.json"), 'w') as f:
        json.dump(session_data, f)
    
    return jsonify({"sessionId": session_id, "studentId": student_id}), 200

@app.route('/api/upload/<session_id>', methods=['POST'])
def upload_video(session_id):
    if 'video' not in request.files:
        return jsonify({"error": "No video provided"}), 400
    
    file = request.files['video']
    student_id = request.form.get('studentId')
    name = request.form.get('name')
    year = request.form.get('year')
    dept = request.form.get('dept')
    
    if not student_id:
        return jsonify({"error": "Registration Number is required"}), 400
    
    # Create student directory
    student_dir = os.path.join(DATA_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)
    
    # Create faces directory named after registration number
    faces_dir = os.path.join(student_dir, student_id)
    os.makedirs(faces_dir, exist_ok=True)
    
    # Get existing session data
    session_file = os.path.join(student_dir, f"{session_id}.json")
    if not os.path.exists(session_file):
        return jsonify({"error": "Invalid session"}), 404
    
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    # Save the original WebM video (temporary)
    webm_filename = f"{student_id}_{session_id}.webm"
    webm_path = os.path.join(student_dir, webm_filename)
    file.save(webm_path)
    print(f"Saved WebM video to {webm_path}")
    
    # Convert WebM to MP4 using FFmpeg
    mp4_filename = f"{student_id}_{session_id}.mp4"
    mp4_path = os.path.join(student_dir, mp4_filename)
    
    try:
        # Run FFmpeg to convert the file
        import subprocess
        cmd = [
            'ffmpeg', 
            '-i', webm_path,  # Input file
            '-c:v', 'libx264',  # Video codec
            '-preset', 'fast',  # Encoding speed/compression trade-off
            '-crf', '23',       # Quality
            '-y',               # Overwrite output without asking
            mp4_path            # Output file
        ]
        
        process = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            print(f"Error converting video: {process.stderr}")
            return jsonify({
                "success": False,
                "message": "Failed to convert video format"
            }), 500
            
        print(f"Converted video to MP4 format: {mp4_path}")
        
        # Delete the WebM file now that conversion is complete
        try:
            os.remove(webm_path)
            print(f"Deleted temporary WebM file: {webm_path}")
        except Exception as e:
            print(f"Warning: Could not delete WebM file: {e}")
        
        # Extract faces from the MP4 video
        faces_count = extract_faces_from_video(
            mp4_path, 
            faces_dir,
            face_confidence=0.3,
            face_padding=0.2
        )
        print(f"Extracted {faces_count} faces from {mp4_path}")
        
        # Update session data
        session_data["videoUploaded"] = True
        session_data["uploadTime"] = datetime.now().isoformat()
        session_data["facesExtracted"] = True
        session_data["facesCount"] = faces_count
        session_data["videoPath"] = mp4_path  # Store video path for reference
        
        # Update additional fields if provided in form data
        if name:
            session_data["name"] = name
        if year:
            session_data["year"] = year
        if dept:
            session_data["dept"] = dept
        
        # Save updated session data
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        # Keep the MP4 video file for reference
        print(f"Keeping MP4 video file for reference: {mp4_path}")
            
        return jsonify({
            "success": True,
            "message": f"Video processed successfully. Extracted {faces_count} face images."
        }), 200
    
    except Exception as e:
        print(f"Error processing video: {e}")
        return jsonify({
            "success": False,
            "message": f"Error processing video: {str(e)}"
        }), 500

@app.route('/api/reset-faces/<session_id>', methods=['POST'])
def reset_faces(session_id):
    student_id = request.json.get('studentId')
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400
    
    # Get path to faces directory using registration number as directory name
    student_dir = os.path.join(DATA_DIR, student_id)
    faces_dir = os.path.join(student_dir, student_id)  # Changed from 'faces' to student_id
    
    if os.path.exists(faces_dir):
        try:
            # Delete all files in faces directory
            for file in os.listdir(faces_dir):
                file_path = os.path.join(faces_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            
            # Reset session data
            session_file = os.path.join(student_dir, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                session_data["facesExtracted"] = False
                session_data["facesCount"] = 0
                session_data["resetTime"] = datetime.now().isoformat()
                
                with open(session_file, 'w') as f:
                    json.dump(session_data, f)
            
            return jsonify({
                "success": True, 
                "message": "Face data reset successfully"
            }), 200
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500
    else:
        return jsonify({
            "error": "Faces directory not found"
        }), 404

@app.route('/qr')
def generate_qr():
    # Generate QR code for the HTTPS URL
    url = f"https://{request.host}"
    img = qrcode.make(url)
    
    # Convert to base64 for display
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Return simple HTML with QR code
    return f"""
    <html>
        <head><title>Scan to connect</title></head>
        <body style="text-align: center; padding: 50px;">
            <h1>Scan this QR code with your phone</h1>
            <img src="data:image/png;base64,{img_str}">
            <p>Or visit: <a href="{url}">{url}</a></p>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)