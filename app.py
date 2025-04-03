from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
from werkzeug.utils import secure_filename
from models import db, User
from flask_cors import CORS
from flask import url_for

# Initialize Flask App
app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
CORS(app, supports_credentials=True)

# Configure PostgreSQL Database
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:postpass@localhost/exam_paper_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key_here'

# Configure Upload Folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Extensions
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Create tables within app context
def create_tables():
    with app.app_context():
        db.create_all()

create_tables()

# User Registration Route
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    required_fields = ["collegeName", "fullName", "role", "distributorReceiverId", "phoneNumber", "email", "username", "password"]
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"message": "All fields are required!"}), 400

    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Username already taken"}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already registered"}), 409
    if User.query.filter_by(phone_number=data['phoneNumber']).first():
        return jsonify({"message": "Phone number already registered"}), 409

    # Create new user
    new_user = User(
        college_name=data['collegeName'],
        full_name=data['fullName'],
        role=data['role'],
        distributor_receiver_id=data['distributorReceiverId'],
        phone_number=data['phoneNumber'],
        email=data['email'],
        username=data['username']
    )
    new_user.set_password(data['password'])  # Hash password

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201

# User Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get("username")).first()

    if user and user.check_password(data.get("password")):
        access_token = create_access_token(identity={
            "id": str(user.id),
            "role": user.role,
            "receiverId": user.distributor_receiver_id
        })

        return jsonify({"access_token": access_token, "role": user.role, "receiverId": user.distributor_receiver_id}), 200

    return jsonify({"message": "Invalid credentials"}), 401

# Upload Exam Paper Route
@app.route('/upload-exam', methods=['POST'])
@jwt_required()
def upload_exam():
    current_user = get_jwt_identity()
    data = request.form
    files = request.files

    receiver_id = data.get("receiverId")
    receiver_name = data.get("receiverName")

    if not files:
        return jsonify({"message": "No files uploaded!"}), 422

    if current_user.get("receiverId") != receiver_id:
        return jsonify({"message": "Unauthorized receiver ID"}), 403

    if not receiver_id or not receiver_name:
        return jsonify({"message": "Missing required fields"}), 400

    exam = {"receiverId": receiver_id, "receiverName": receiver_name}

    for set_name in ["setA", "setB", "setC"]:
        file = request.files.get(set_name)
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            exam[set_name] = url_for('download_file', filename=filename, _external=True)

    return jsonify({"message": "Exam uploaded successfully!", "exam": exam}), 201

# Fetch Exam Papers for a Specific Receiver
@app.route('/get-exams', methods=['GET'])
@jwt_required()
def get_exams():
    current_user = get_jwt_identity()
    receiver_id = current_user.get("receiverId")

    if not receiver_id:
        return jsonify({"message": "Receiver ID is required"}), 400

    exams = [
        {
            "receiverId": receiver_id,
            "receiverName": "Receiver Example",
            "setA": "/uploads/sample_setA.pdf",
            "setB": "/uploads/sample_setB.pdf",
            "setC": "/uploads/sample_setC.pdf"
        }
    ]

    return jsonify(exams)

# File Download Route
@app.route('/download/<filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    current_user = get_jwt_identity()

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"message": "File not found"}), 404

    if str(current_user.get("receiverId")) not in filename:
        return jsonify({"message": "Unauthorized access"}), 403

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    print(app.url_map)  # Debugging: Show available routes
    app.run(debug=True)