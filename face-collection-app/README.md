# Face Collection Application

A comprehensive system for collecting, processing, and organizing facial images from video recordings for educational institutions.

## Overview

This application allows educational institutions to efficiently collect facial data from students through a simple web interface. It captures video recordings of students' faces, processes them to extract individual face images, and organizes them for later use in facial recognition systems or other biometric applications.

## Features

- **User-Friendly Web Interface**: Simple registration form for collecting student details
- **Guided Recording Process**: Step-by-step instructions for proper facial video recording
- **Real-Time Video Capture**: Uses device camera to record student faces from multiple angles and expressions
- **Automated Face Extraction**: Processes videos to extract standardized face images using YOLO
- **Organized Data Storage**: Systematically organizes collected data by student ID
- **Progress Tracking**: Visual feedback during recording and processing
- **Retry Functionality**: Option to retry video recording if needed

## System Architecture

### Frontend

- HTML5, CSS3, and vanilla JavaScript
- Responsive design that works on both desktop and mobile devices
- MediaRecorder API for client-side video recording

### Backend

- Flask server for handling API requests
- YOLO (You Only Look Once) model for face detection
- OpenCV for image processing and manipulation

### Data Storage

- Organized directory structure by student ID
- JSON metadata for session tracking
- Standardized face image format (128x128 grayscale)

## Directory Structure

```
face-collection-app/
├── data/                  # Storage for student data
│   └── {student_id}/      # Individual student folders
│       ├── {student_id}/  # Extracted face images
│       ├── *.json         # Session metadata
│       └── *.mp4          # Processed video recordings
├── reports/               # Generated reports
├── server/                # Backend server
│   ├── static/            # Frontend assets
│   │   ├── css/           # Stylesheets
│   │   ├── js/            # JavaScript files
│   │   └── index.html     # Main application page
│   ├── app.py             # Flask application
│   ├── cert.pem           # SSL certificate (for HTTPS)
│   └── key.pem            # SSL private key (for HTTPS)
├── yolo/                  # YOLO model files
│   └── weights/           # Pre-trained YOLO weights
└── data_split.py          # Utility script for organizing data
```

## Installation & Setup

### Prerequisites

- Python 3.8+
- FFmpeg (for video processing)
- CUDA-compatible GPU (optional, for faster processing)

### Installation Steps

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/face-collection-app.git
   cd face-collection-app
   ```
2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```
4. Download the YOLO model weights:

   ```
   mkdir -p yolo/weights
   # Place the yolo11n-face.pt file in the yolo/weights directory
   ```
5. Generate self-signed certificates for HTTPS (optional but recommended):

   ```
   openssl req -x509 -newkey rsa:4096 -nodes -out server/cert.pem -keyout server/key.pem -days 365
   ```

### Running the Application

1. Start the Flask server:

   ```
   cd server
   python app.py
   ```
2. Access the application:

   - Local development: https://localhost:5000
   - For accessing from other devices, use the /qr endpoint to generate a QR code

## Usage Guide

1. **Student Registration**:

   - Enter student registration number (ID)
   - Fill in name, year, and department details
   - Click "Start" to proceed
2. **Recording Process**:

   - Grant camera access permissions when prompted
   - Follow the on-screen instructions for positioning and movements
   - Click "Start Recording" when ready
   - Complete the 15-second recording sequence
   - Face images will be automatically extracted after processing
3. **Data Organization**:

   - Run the data_split.py script to organize collected data by year:
     ```
     python data_split.py
     ```
   - This script also generates reports about the collection status

## Data Processing

1. **Video Recording**:

   - 15-second WebM video recorded on the client
   - Includes multiple angles and expressions
2. **Video Processing**:

   - WebM converted to MP4 using FFmpeg
   - Frames extracted at regular intervals
3. **Face Detection**:

   - YOLO model used to detect faces in video frames
   - Haar cascade used as fallback detection method
4. **Face Normalization**:

   - Detected faces cropped with padding
   - Converted to grayscale
   - Resized to 128x128 pixels
   - Saved as individual JPG files

## Security & Privacy

- Data is stored locally, not sent to external servers
- HTTPS recommended for secure device camera access
- Consider implementing access controls for production use

## Acknowledgments

- YOLO (You Only Look Once) for face detection
- Flask for the backend framework
- MediaRecorder API for in-browser recording
