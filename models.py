from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime 


db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    college_name = db.Column(db.String(100), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    distributor_receiver_id = db.Column(db.String(50), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)
    
 

class ExamPaper(db.Model):
    __tablename__ = 'exam_paper'  # Explicit table name
    
    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.String(50), nullable=False)  # Note: Corrected from 'recelver_id'
    receiver_name = db.Column(db.String(100), nullable=True)  # Assuming optional
    set_name = db.Column(db.String(10), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    subject_name = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)  # Recommended addition
    
    # Optional: Relationship to User if receiver_id references users
    # receiver = db.relationship('User', foreign_keys=[receiver_id], 
    #                          primaryjoin="ExamPaper.receiver_id==User.distributor_receiver_id",
    #                          backref='exam_papers')
    
    def __repr__(self):
        return f"<ExamPaper {self.filename} (Set {self.set_name})>"