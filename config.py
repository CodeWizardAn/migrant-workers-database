import os

# Get the base directory of your project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Database will be created inside your SIH folder
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Secret key for sessions & security
    SECRET_KEY = "supersecretkey"
