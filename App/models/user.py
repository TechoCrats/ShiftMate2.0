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

    def __init__(self, username, password=None, isAdmin=False):
        self.username = username
        self.isAdmin = isAdmin
        if password:  
            self.set_password(password)

    def get_json(self):
        return{
            'id': self.id,
            'username': self.username,
            'isAdmin': self.isAdmin
        }

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def is_authenticated_admin(self):
        return self.isAdmin
