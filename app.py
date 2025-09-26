from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import qrcode

# -------------------- Flask app setup --------------------
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database config
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Upload folder
UPLOAD_FOLDER = os.path.join(BASE_DIR, "documents")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------- Database models --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    govt_id = db.Column(db.String(50))
    language = db.Column(db.String(20), default="english")
    documents = db.relationship("Document", backref="user", lazy=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    filename = db.Column(db.String(200))
    date = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# -------------------- Create DB tables --------------------
with app.app_context():
    db.create_all()

# -------------------- Routes --------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        name = request.form.get("name")
        age = request.form.get("age")
        govt_id = request.form.get("govt_id")

        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for("register"))

        user = User(username=username, password=password, name=name, age=age, govt_id=govt_id)
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("language"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/language", methods=["GET", "POST"])
def language():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        lang = request.form.get("language")
        user.language = lang
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("language.html", current_user=user)

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    return render_template("home.html", current_user=user)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")
        date = request.form.get("date")

        if not file or file.filename == "":
            flash("No file selected!", "danger")
            return redirect(url_for("upload"))

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        try:
            file.save(save_path)
        except Exception as e:
            flash(f"Error saving file: {e}", "danger")
            return redirect(url_for("upload"))

        doc = Document(title=title, filename=filename, user_id=user.id, date=date)
        db.session.add(doc)
        db.session.commit()

        flash("Document uploaded successfully!", "success")
        return redirect(url_for("view_docs"))

    docs = Document.query.filter_by(user_id=user.id).all()
    return render_template("upload.html", current_user=user, docs=docs)

@app.route("/documents")
def view_docs():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    docs = Document.query.filter_by(user_id=user.id).all()
    return render_template("documents.html", current_user=user, docs=docs)

@app.route("/documents/<filename>")
def get_document(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    return render_template("profile.html", current_user=user)

# -------------------- Profile QR opens website --------------------
@app.route("/profile_qr/<int:user_id>")
def profile_qr(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("profile.html", current_user=user)

@app.route("/qr")
def qr():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    # QR now points to the live profile URL
    profile_link = url_for('profile_qr', user_id=user.id, _external=True)
    img = qrcode.make(profile_link)
    qr_path = os.path.join(app.config["UPLOAD_FOLDER"], f"qr_{user.username}.png")
    img.save(qr_path)
    return send_from_directory(app.config["UPLOAD_FOLDER"], f"qr_{user.username}.png")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("index"))

@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    # Delete user documents
    for doc in user.documents:
        path = os.path.join(app.config["UPLOAD_FOLDER"], doc.filename)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(user)
    db.session.commit()
    session.pop("user_id", None)
    flash("Account deleted permanently", "success")
    return redirect(url_for("index"))

# -------------------- Run app --------------------
if __name__ == "__main__":
    app.run(debug=True)
