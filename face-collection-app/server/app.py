import os
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import qrcode
from io import BytesIO
import base64

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

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
    
    # Create session info
    session_data = {
        "sessionId": session_id,
        "regNo": student_id,
        "name": name,
        "year": year,
        "dept": dept,
        "startTime": datetime.now().isoformat(),
        "videoUploaded": False
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
    
    # Save video
    student_dir = os.path.join(DATA_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)
    
    # Get existing session data
    session_file = os.path.join(student_dir, f"{session_id}.json")
    if not os.path.exists(session_file):
        return jsonify({"error": "Invalid session"}), 404
    
    with open(session_file, 'r') as f:
        session_data = json.load(f)
    
    # Update session data
    session_data["videoUploaded"] = True
    session_data["uploadTime"] = datetime.now().isoformat()
    
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
    
    # Save the video with more descriptive filename
    video_path = os.path.join(student_dir, f"{session_id}_{student_id}_{dept}_{year}yr.webm")
    file.save(video_path)
    
    return jsonify({
        "success": True,
        "message": "Video uploaded successfully"
    }), 200

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
    app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))