from werkzeug.security import check_password_hash, generate_password_hash
from App.database import db
from datetime import datetime, date, time

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username =  db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)
    isAdmin = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<User id={self.id} username={self.username!r} admin={self.isAdmin}>"


    def __init__(self, username, password, isAdmin=False):
        self.username = username
        self.isAdmin = isAdmin
        if password:  
            self.set_password(password)

    def get_json(self):
        return {
            'id': self.id,
            'username': self.username
        }

    def set_password(self, password):
        self.password = generate_password_hash(password)  # default pbkdf2:sha256
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_authenticated_admin(self):
        return self.isAdmin
