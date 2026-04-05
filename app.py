from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import datetime
import json  # Add this import
from models import db, User, ExamPaper
import logging


def load_dotenv(dotenv_path='.env'):
    """Load key=value pairs from a .env file into os.environ if missing."""
    if not os.path.exists(dotenv_path):
        return

    with open(dotenv_path, 'r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value

# Initialize Flask App
app = Flask(__name__)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

# Configurations
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://postgres:postpass@localhost/exam_paper_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change-me-jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
app.config['JWT_IDENTITY_CLAIM'] = 'identity'  # Add this line to allow dictionary identity
app.config['AWS_REGION'] = os.getenv('AWS_REGION', '')
app.config['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME', '')
app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', '')
app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', '')
app.config['FRONTEND_ORIGIN'] = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')

CORS(app, origins=["http://13.53.112.235"])

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}  # Supported file types
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Initialize Extensions
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# [Keep all your helper functions and other routes the same...]

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"message": "Username and password required"}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({"message": "Invalid credentials"}), 401

    try:
        # Create identity dictionary
        identity = {
            "id": str(user.id),
            "role": user.role,
            "receiverId": user.distributor_receiver_id,
            "username": user.username
        }
        
        # Create token with the identity dictionary
        access_token = create_access_token(identity=identity)
        
        return jsonify({
            "access_token": access_token,
            "role": user.role,
            "receiverId": user.distributor_receiver_id,
            "userId": str(user.id)
        }), 200
    except Exception as e:
        app.logger.error(f"Token creation error: {str(e)}")
        return jsonify({"message": "Login failed"}), 500

# Helper function
def allowed_file(filename):
    """Check if filename has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


    
# @app.route('/upload-exam', methods=['POST'])
# @jwt_required()
# def upload_exam():
#     try:
#         current_user = get_jwt_identity()
#         if not current_user or not isinstance(current_user, dict):
#             return jsonify({"message": "Invalid token"}), 401

#         # Validate at least one file exists
#         if not any(f in request.files for f in ['setA', 'setB', 'setC']):
#             return jsonify({"message": "No files uploaded"}), 400

#         data = request.form
#         if not data.get("receiverId") or not data.get("subject"):
#             return jsonify({"message": "Receiver ID and subject are required"}), 400

#         exam_data = {
#             "receiverId": data["receiverId"],
#             "subject": data["subject"],
#             "files": []
#         }

#         # Get receiver name if available (you might need to fetch from User table)
#         receiver_name = data.get("receiverName", "")

#         for set_name in ["setA", "setB", "setC"]:
#             file = request.files.get(set_name)
#             if file and file.filename != '':
#                 if not allowed_file(file.filename):
#                     return jsonify({
#                         "message": f"Invalid file type for {set_name}",
#                         "allowed": list(app.config['ALLOWED_EXTENSIONS'])
#                     }), 400
                
#                 # Generate secure filename
#                 filename = secure_filename(f"{data['receiverId']}_{data['subject']}_{set_name}_{file.filename}")
#                 file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 file.save(file_path)
                
#                 # Create and save ExamPaper record
#                 exam_record = ExamPaper(
#                     receiver_id=data["receiverId"],
#                     receiver_name=receiver_name,
#                     set_name=set_name,
#                     filename=filename,
#                     filepath=file_path,
#                     subject_name=data["subject"]
#                 )
#                 db.session.add(exam_record)
                
#                 exam_data["files"].append({
#                     "set": set_name,
#                     "filename": filename,
#                     "url": url_for('download_file', filename=filename, _external=True)
#                 })

#         # Commit all database changes
#         db.session.commit()

#         return jsonify({
#             "message": "Upload successful",
#             "exam": exam_data
#         }), 201

#     except Exception as e:
#         db.session.rollback()  # Important: Rollback on error
#         app.logger.error(f"Upload error: {str(e)}", exc_info=True)
#         return jsonify({"message": f"Upload failed: {str(e)}"}), 500   
# 
#


@app.route('/upload-exam', methods=['POST'])
@jwt_required()
def upload_exam():
    try:
        current_user = get_jwt_identity()
        if not current_user or not isinstance(current_user, dict):
            return jsonify({"message": "Invalid token"}), 401

        # Validate at least one file exists
        if not any(f in request.files for f in ['setA', 'setB', 'setC']):
            return jsonify({"message": "No files uploaded"}), 400

        data = request.form
        if not data.get("receiverId") or not data.get("subject"):
            return jsonify({"message": "Receiver ID and subject are required"}), 400

        # Check for existing papers for the same subject and sets
        existing_sets = set()
        for set_name in ["setA", "setB", "setC"]:
            if request.files.get(set_name) and request.files[set_name].filename != '':
                # Check if this set for this subject already exists
                existing = ExamPaper.query.filter_by(
                    receiver_id=data["receiverId"],
                    subject_name=data["subject"],
                    set_name=set_name
                ).first()
                
                if existing:
                    existing_sets.add(set_name)
        
        if existing_sets:
            return jsonify({
                "message": f"Already submitted papers for subject '{data['subject']}' sets: {', '.join(existing_sets)}",
                "conflict_sets": list(existing_sets)
            }), 409  # 409 Conflict status code

        exam_data = {
            "receiverId": data["receiverId"],
            "subject": data["subject"],
            "files": []
        }

        for set_name in ["setA", "setB", "setC"]:
            file = request.files.get(set_name)
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    return jsonify({
                        "message": f"Invalid file type for {set_name}",
                        "allowed": list(app.config['ALLOWED_EXTENSIONS'])
                    }), 400
                
                filename = secure_filename(f"{data['receiverId']}_{data['subject']}_{set_name}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                exam_record = ExamPaper(
                    receiver_id=data["receiverId"],
                    receiver_name=data.get("receiverName", ""),
                    set_name=set_name,
                    filename=filename,
                    filepath=file_path,
                    subject_name=data["subject"]
                )
                db.session.add(exam_record)
                
                exam_data["files"].append({
                    "set": set_name,
                    "filename": filename,
                    "url": url_for('download_file', filename=filename, _external=True)
                })

        db.session.commit()

        return jsonify({
            "message": "Upload successful",
            "exam": exam_data
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Upload error: {str(e)}", exc_info=True)
        return jsonify({"message": f"Upload failed: {str(e)}"}), 500

@app.route('/get-exams', methods=['GET'])
@jwt_required()
def get_exams():
    receiver_id = request.args.get("receiverId")
    current_user = get_jwt_identity()

    if not receiver_id:
        return jsonify({"message": "Receiver ID is required"}), 422

    if current_user.get("receiverId") != receiver_id:
        return jsonify({"message": "Unauthorized access"}), 403

    # Scan the uploads folder for files matching receiverId
    matched_files = []
    for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
        if filename.startswith(f"{receiver_id}_"):
            parts = filename.split("_")
            if len(parts) >= 2:
                set_name = parts[2]  # "setA", "setB", etc.
                matched_files.append({
                    "setName": set_name,
                    "filename": filename,
                    "downloadUrl": url_for('download_file', filename=filename, _external=True)
                })

    # Group files into exam objects
    exams = []
    if matched_files:
        exam = {
            "receiverId": receiver_id,
            "receiver": current_user,
            "files": matched_files
        }
        exams.append(exam)

    return jsonify({"exams": exams}), 200

@app.route('/download/<filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    try:
        current_user = get_jwt_identity()
        if not current_user or not isinstance(current_user, dict):
            return jsonify({"message": "Invalid token"}), 401

        # Verify user has access to this file
        if str(current_user.get("receiverId")) not in filename:
            return jsonify({"message": "Unauthorized access"}), 403

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({"message": "File not found"}), 404

        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({"message": "Download failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)