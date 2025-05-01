import os, time, pickle
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Load environment variables
load_dotenv()

# Flask setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "fallbacksecret")

# DB setup
project_dir = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(project_dir, 'virtualvault.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Mail setup
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='ukashaworkspace@gmail.com',
    MAIL_PASSWORD='kfmu txwk zkcw bdcw'
)
mail = Mail(app)

# Allowed file types
app.config['ALLOWED_EXTENSIONS'] = {
    'txt', 'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp',
    'zip', 'rar', 'tar', 'gz',
    'mp3', 'wav', 'mp4', 'mov', 'avi', 'mkv',
    'csv', 'json', 'xml', 'yaml', 'yml',
    'py', 'java', 'c', 'cpp', 'js', 'ts', 'html', 'css', 'php', 'rb', 'go', 'sh', 'swift', 'sql', 'ipynb',
    'md', 'rst'
}
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    drive_folder_id = db.Column(db.String(100))  # New
    files = db.relationship('File', backref='user', lazy=True)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_name = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)   
    drive_file_id = db.Column(db.String(100), nullable=True)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# Google Drive upload helper
def get_drive_service():
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_to_drive(file_stream, filename, user):
    service = get_drive_service()
    user_folder_id = get_or_create_user_folder(service, user)

    file_metadata = {
        'name': filename,
        'parents': [user_folder_id]
    }

    media = MediaIoBaseUpload(file_stream, mimetype='application/octet-stream')
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    service.permissions().create(
        fileId=uploaded_file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    return uploaded_file['webViewLink'], uploaded_file['id']


def get_or_create_user_folder(service, user):
    if user.drive_folder_id:
        return user.drive_folder_id

    parent_id = os.getenv("GDRIVE_PARENT_FOLDER_ID")
    folder_metadata = {
        'name': f"User_{user.id}_{user.name}",
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    user.drive_folder_id = folder['id']
    db.session.commit()
    return folder['id']


# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name, email, message = request.form['name'], request.form['email'], request.form['message']
        db.session.add(Contact(name=name, email=email, message=message))
        db.session.commit()
        mail.send(Message("New Contact Form Submission", sender=email, recipients=["your_admin_email@example.com"], body=f"{name} ({email}) says:\n{message}"))
        flash('Thank you for contacting us!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/reviews')
def reviews():
    return render_template('reviews.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name, email, password, confirm = request.form['username'], request.form['email'], request.form['password'], request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('login'))
        db.session.add(User(name=name, email=email, password=password))
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'], password=request.form['password']).first()
        if user:
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Log in first.', 'error')
        return redirect(url_for('home'))
    user = User.query.get(session['user_id'])
    files = File.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', user=user, files=files)


@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        flash('Log in to upload files.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(request.url)

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = str(int(time.time()))
        unique_filename = f"{timestamp}_{filename}"

        file.stream.seek(0)
        link, drive_file_id = upload_to_drive(io.BytesIO(file.read()), unique_filename, user)

        db.session.add(File(
            user_id=user.id,
            file_name=unique_filename,
            file_path=link,
            drive_file_id=drive_file_id
        ))
        db.session.commit()
        flash('File uploaded to Google Drive!', 'success')
    else:
        flash('File type not allowed.', 'error')

    return redirect(url_for('dashboard'))


@app.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    if 'user_id' not in session:
        flash('Log in required.', 'error')
        return redirect(url_for('login'))

    file = File.query.get(file_id)
    if file and file.user_id == session['user_id']:
        # Delete from Google Drive
        try:
            if file.drive_file_id:
                service = get_drive_service()
                service.files().delete(fileId=file.drive_file_id).execute()
        except Exception as e:
            flash(f"Google Drive deletion error: {e}", 'error')

        db.session.delete(file)
        db.session.commit()
        flash('File deleted from app and Drive.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/preview_file/<int:file_id>')
def preview_file(file_id):
    if 'user_id' not in session:
        flash('Log in required.', 'error')
        return redirect(url_for('login'))
    file = File.query.get(file_id)
    if file and file.user_id == session['user_id']:
        return redirect(file.file_path)
    flash('File not found or unauthorized.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.', 'success')
    return redirect(url_for('home'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    app.run(debug=True)
