from flask import Flask, request, render_template, jsonify, current_app, redirect, url_for, session
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps
import random
import string

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Required for session management

# Configure CORS to allow all origins
CORS(app, resources={r"/api/*": {"origins": "*"}})

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.library_db

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to convert ObjectId to string
def serialize_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    return obj

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email(subject, body, to_email):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Login route
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('userId')
        password = request.form.get('password')
        
        # Special case for admin
        if user_id == "admin" and password == "admin123":
            session['user_id'] = user_id
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        
        # Find user in database
        user = db.users.find_one({'userId': user_id})
        
        if user and user.get('password') == password:
            session['user_id'] = user_id
            session['role'] = user.get('role', 'user')
            session['name'] = user.get('name', '')
            
            # Redirect based on role
            if user.get('role') == 'staff':
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            return render_template("login.html", error="Invalid user ID or password")
    
    return render_template("login.html")

# Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('public_index'))

# Page Routes
@app.route("/")
def public_index():
    return render_template("index.html")

@app.route("/admin")
@login_required
def admin_dashboard():
    try:
        # Get counts for dashboard
        users_count = db.users.count_documents({})
        books_count = db.books.count_documents({})
        
        # Get recently added books (last 5)
        recent_books = list(db.books.find().sort('created_at', -1).limit(5))
        for book in recent_books:
            book['_id'] = str(book['_id'])
            if book.get('cover_image'):
                book['cover_image'] = book['cover_image'].replace('\\', '/')
        
        return render_template("adminDashboard.html",
                             users_count=users_count,
                             books_count=books_count,
                             recent_books=recent_books)
    except Exception as e:
        print(f"Error in admin dashboard: {str(e)}")
        return render_template("adminDashboard.html",
                             users_count=0,
                             books_count=0,
                             recent_books=[],
                             error=str(e))

@app.route("/api/pages")
def get_pages():
    pages = [
        {
            "name": "Dashboard",
            "path": "/",
            "icon": "fas fa-home"
        },
        {
            "name": "Users",
            "path": "/users",
            "icon": "fas fa-users"
        },
        {
            "name": "Add User",
            "path": "/add_user",
            "icon": "fas fa-user-plus"
        },
        {
            "name": "Books",
            "path": "/books",
            "icon": "fas fa-book"
        },
        {
            "name": "Add Book",
            "path": "/add_book",
            "icon": "fas fa-book-medical"
        }
    ]
    return jsonify(pages)

@app.route('/users')
def users():
    try:
        # Get all users from the database
        users = list(db.users.find())
        
        # Convert ObjectId to string for each user
        for user in users:
            user['_id'] = str(user['_id'])
        
        # Check user role and render appropriate template
        if session.get('role') == 'admin':
            return render_template('users.html', users=users)
        else:
            return render_template('staff_users.html', users=users)
            
    except Exception as e:
        print(f"Error in users route: {str(e)}")
        return render_template('users.html', users=[], error="Error fetching users")

@app.route("/api/users")
def get_users():
    try:
        users = list(db.users.find())
        users = [{**user, '_id': serialize_id(user['_id'])} for user in users]
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_user")
@login_required
def add_user():
    return render_template("add_user.html")

@app.route('/books')
def books():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get filter parameters
        department = request.args.get('department')
        search = request.args.get('search')
        
        # Build query
        query = {}
        if department:
            query['department'] = department
            
        if search:
            query['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'author': {'$regex': search, '$options': 'i'}},
                {'isbn': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get books from database
        books = list(db.books.find(query))
        
        # Convert ObjectId to string for JSON serialization
        for book in books:
            book['_id'] = str(book['_id'])
            # Convert backslashes to forward slashes for cover_image paths
            if 'cover_image' in book and book['cover_image']:
                book['cover_image'] = book['cover_image'].replace('\\', '/')
        
        # Get unique departments for filter dropdown
        departments = sorted(db.books.distinct('department'))
        
        # Get user role
        user_role = session.get('role')
        
        # Render appropriate template based on user role
        if user_role == 'admin':
            return render_template('books.html', books=books, departments=departments)
        else:
            return render_template('staff_books.html', books=books, departments=departments)
            
    except Exception as e:
        print(f"Error in books route: {str(e)}")
        return render_template('books.html', books=[], departments=[], error="An error occurred while fetching books.")

@app.route("/api/books")
def get_books():
    try:
        books = list(db.books.find())
        books = [{**book, '_id': serialize_id(book['_id'])} for book in books]
        return jsonify(books)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_book")
@login_required
def add_book():
    return render_template("add_book.html")

def generate_password(length=8):
    """Generate a random password with letters, numbers, and special characters"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def send_user_credentials(user_data, password):
    """Send user credentials via email"""
    subject = "Your Library Management System Account"
    body = f"""
    <h2>Welcome to Library Management System</h2>
    <p>Dear {user_data['name']},</p>
    <p>Your account has been created successfully. Here are your login credentials:</p>
    <ul>
        <li><strong>User ID:</strong> {user_data['userId']}</li>
        <li><strong>Password:</strong> {password}</li>
    </ul>
    <p>Please change your password after your first login for security purposes.</p>
    <p>Best regards,<br>Library Management System Team</p>
    """
    return send_email(subject, body, user_data['email'])

# User Management Routes
@app.route('/users/add', methods=['POST'])
def create_user():
    try:
        # Generate a random password
        password = generate_password()
        
        user_data = {
            'userId': request.form.get('userId'),
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'role': request.form.get('role'),
            'password': password  # Store the password (in production, use proper hashing)
        }
        
        # Validate required fields
        required_fields = ['userId', 'name', 'email', 'role']
        for field in required_fields:
            if not user_data[field]:
                return render_template("add_user.html", error=f"Missing required field: {field}")
            
        # Check if user with same userId already exists
        existing_user = db.users.find_one({'userId': user_data['userId']})
        if existing_user:
            return render_template("add_user.html", error="User with this ID already exists")
            
        # Check if user with same email already exists
        existing_email = db.users.find_one({'email': user_data['email']})
        if existing_email:
            return render_template("add_user.html", error="User with this email already exists")
            
        # Insert the user
        db.users.insert_one(user_data)
        
        # Send email with credentials
        if send_user_credentials(user_data, password):
            return render_template("users.html", users=list(db.users.find()), message="User added successfully! Credentials sent to user's email.")
        else:
            return render_template("users.html", users=list(db.users.find()), message="User added successfully! But failed to send email credentials.")
            
    except Exception as e:
        print(f"Error in create_user: {str(e)}")
        return render_template("add_user.html", error=str(e))

@app.route('/api/users/add', methods=['POST'])
def api_create_user():
    try:
        # Generate a random password
        password = generate_password()
        
        user_data = request.json
        required_fields = ['userId', 'name', 'email', 'role']
        
        # Validate required fields
        for field in required_fields:
            if not user_data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
            
        # Check if user with same userId already exists
        existing_user = db.users.find_one({'userId': user_data['userId']})
        if existing_user:
            return jsonify({"error": "User with this ID already exists"}), 400
            
        # Check if user with same email already exists
        existing_email = db.users.find_one({'email': user_data['email']})
        if existing_email:
            return jsonify({"error": "User with this email already exists"}), 400
            
        # Add password to user data
        user_data['password'] = password
        
        # Insert the user
        result = db.users.insert_one(user_data)
        user_data['_id'] = serialize_id(result.inserted_id)
        
        # Send email with credentials
        email_sent = send_user_credentials(user_data, password)
        
        response_data = {
            "message": "User added successfully",
            "user": user_data,
            "email_sent": email_sent
        }
        
        return jsonify(response_data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            user['_id'] = serialize_id(user['_id'])
            return render_template("edit_user.html", user=user)
        return render_template("users.html", users=list(db.users.find()), error="User not found")
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return render_template("users.html", users=list(db.users.find()), error=str(e))

@app.route('/api/users/<user_id>', methods=['GET'])
def api_get_user(user_id):
    try:
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            user['_id'] = serialize_id(user['_id'])
            return jsonify(user)
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users/<user_id>/edit', methods=['POST'])
def update_user(user_id):
    try:
        user_data = {
            'userId': request.form.get('userId'),
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'role': request.form.get('role')
        }
        
        # Validate required fields
        required_fields = ['userId', 'name', 'email', 'role']
        for field in required_fields:
            if not user_data[field]:
                return render_template("edit_user.html", user=user_data, error=f"Missing required field: {field}")
        
        # Check if new password is provided
        new_password = request.form.get('password')
        if new_password:
            user_data['password'] = new_password
            # Send email notification about password change
            email_subject = "Your Library Management System Password Has Been Updated"
            email_body = f"""
            <h2>Password Update Notification</h2>
            <p>Dear {user_data['name']},</p>
            <p>Your password has been updated by the administrator. Here are your new login credentials:</p>
            <ul>
                <li><strong>User ID:</strong> {user_data['userId']}</li>
                <li><strong>New Password:</strong> {new_password}</li>
            </ul>
            <p>Please change your password after your next login for security purposes.</p>
            <p>Best regards,<br>Library Management System Team</p>
            """
            send_email(email_subject, email_body, user_data['email'])
        
        # Update the user
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': user_data}
        )
        
        if result.modified_count:
            return redirect('/users')
        return render_template("users.html", users=list(db.users.find()), error="User not found")
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return render_template("users.html", users=list(db.users.find()), error=str(e))

@app.route('/api/users/<user_id>/edit', methods=['PUT'])
def api_update_user(user_id):
    try:
        user_data = request.json
        required_fields = ['userId', 'name', 'email', 'role']
        
        # Validate required fields
        for field in required_fields:
            if not user_data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Update the user
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': user_data}
        )
        
        if result.modified_count:
            user_data['_id'] = user_id
            return jsonify({"message": "User updated successfully", "user": user_data})
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users/<user_id>/delete', methods=['POST'])
def delete_user(user_id):
    try:
        result = db.users.delete_one({'_id': ObjectId(user_id)})
        if result.deleted_count:
            return render_template("users.html", users=list(db.users.find()), message="User deleted successfully!")
        return render_template("users.html", users=list(db.users.find()), error="User not found")
    except Exception as e:
        print(f"Error in delete_user: {str(e)}")
        return render_template("users.html", users=list(db.users.find()), error=str(e))

@app.route('/api/users/<user_id>/delete', methods=['DELETE'])
def api_delete_user(user_id):
    try:
        result = db.users.delete_one({'_id': ObjectId(user_id)})
        if result.deleted_count:
            return jsonify({"message": "User deleted successfully"})
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Book Management Routes
@app.route('/books/add', methods=['POST'])
def create_book():
    try:
        # Handle file upload
        cover_image = request.files.get('cover_image')
        cover_image_path = None
        
        if cover_image and allowed_file(cover_image.filename):
            filename = secure_filename(cover_image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            # Use forward slashes for web paths
            cover_image_path = os.path.join('uploads', unique_filename).replace('\\', '/')
            cover_image.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        book_data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'isbn': request.form.get('isbn'),
            'department': request.form.get('department'),
            'book_count': int(request.form.get('book_count', 1)),
            'borrowed_count': 0,
            'cover_image': cover_image_path,
            'created_at': datetime.now()
        }
        
        # Validate required fields
        required_fields = ['title', 'author', 'isbn', 'department', 'book_count']
        for field in required_fields:
            if not book_data[field]:
                return render_template("add_book.html", error=f"Missing required field: {field}")
        
        # Insert the book
        db.books.insert_one(book_data)
        
        # Send email notification
        email_subject = "New Book Added to Library"
        email_body = f"""
        <h2>New Book Added</h2>
        <p>A new book has been added to the library:</p>
        <ul>
            <li><strong>Title:</strong> {book_data['title']}</li>
            <li><strong>Author:</strong> {book_data['author']}</li>
            <li><strong>ISBN:</strong> {book_data['isbn']}</li>
            <li><strong>Department:</strong> {book_data['department']}</li>
            <li><strong>Copies:</strong> {book_data['book_count']}</li>
        </ul>
        """
        send_email(email_subject, email_body, ADMIN_EMAIL)
        
        return redirect(url_for('books', message="Book added successfully!"))
    except Exception as e:
        print(f"Error in create_book: {str(e)}")
        return render_template("add_book.html", error=str(e))

@app.route('/api/books/add', methods=['POST'])
def api_create_book():
    try:
        book_data = request.json
        required_fields = ['title', 'author', 'isbn', 'book_count']
        
        # Validate required fields
        for field in required_fields:
            if not book_data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Add additional fields
        book_data['borrowed_count'] = 0
        book_data['created_at'] = datetime.now()
        
        # Insert the book
        result = db.books.insert_one(book_data)
        book_data['_id'] = serialize_id(result.inserted_id)
        
        # Send email notification
        email_subject = "New Book Added to Library"
        email_body = f"""
        <h2>New Book Added</h2>
        <p>A new book has been added to the library:</p>
        <ul>
            <li><strong>Title:</strong> {book_data['title']}</li>
            <li><strong>Author:</strong> {book_data['author']}</li>
            <li><strong>ISBN:</strong> {book_data['isbn']}</li>
            <li><strong>Copies:</strong> {book_data['book_count']}</li>
        </ul>
        """
        send_email(email_subject, email_body, ADMIN_EMAIL)
        
        return jsonify({"message": "Book added successfully", "book": book_data}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/books/<book_id>/edit', methods=['POST'])
def update_book(book_id):
    try:
        # Handle file upload
        cover_image = request.files.get('cover_image')
        cover_image_path = None
        
        if cover_image and allowed_file(cover_image.filename):
            filename = secure_filename(cover_image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            # Use forward slashes for web paths
            cover_image_path = os.path.join('uploads', unique_filename).replace('\\', '/')
            cover_image.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

        book_data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'isbn': request.form.get('isbn'),
            'department': request.form.get('department'),
            'book_count': int(request.form.get('book_count', 1))
        }
        
        # Add cover image path if new image was uploaded
        if cover_image_path:
            book_data['cover_image'] = cover_image_path
        
        # Validate required fields
        required_fields = ['title', 'author', 'isbn', 'department', 'book_count']
        for field in required_fields:
            if not book_data[field]:
                return render_template("edit_book.html", book=book_data, error=f"Missing required field: {field}")
        
        # Update the book
        result = db.books.update_one(
            {'_id': ObjectId(book_id)},
            {'$set': book_data}
        )
        
        if result.modified_count:
            return render_template("books.html", books=list(db.books.find()), error="Book details updated successfully!")
    except Exception as e:
        print(f"Error in update_book: {str(e)}")
        return render_template("books.html", books=list(db.books.find()), error=str(e))

@app.route('/api/books/<book_id>/edit', methods=['PUT'])
def api_update_book(book_id):
    try:
        book_data = request.json
        required_fields = ['title', 'author', 'isbn', 'status']
        
        # Validate required fields
        for field in required_fields:
            if not book_data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Update the book
        result = db.books.update_one(
            {'_id': ObjectId(book_id)},
            {'$set': book_data}
        )
        
        if result.modified_count:
            book_data['_id'] = book_id
            return jsonify({"message": "Book updated successfully", "book": book_data})
        return jsonify({"error": "Book not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/books/<book_id>/delete', methods=['POST'])
def delete_book(book_id):
    try:
        result = db.books.delete_one({'_id': ObjectId(book_id)})
        if result.deleted_count:
            return render_template("books.html", books=list(db.books.find()), message="Book deleted successfully!")
        return render_template("books.html", books=list(db.books.find()), error="Book not found")
    except Exception as e:
        print(f"Error in delete_book: {str(e)}")
        return render_template("books.html", books=list(db.books.find()), error=str(e))

@app.route('/api/books/<book_id>/delete', methods=['DELETE'])
def api_delete_book(book_id):
    try:
        result = db.books.delete_one({'_id': ObjectId(book_id)})
        if result.deleted_count:
            return jsonify({"message": "Book deleted successfully"})
        return jsonify({"error": "Book not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/books/<book_id>', methods=['GET'])
def get_book(book_id):
    try:
        book = db.books.find_one({'_id': ObjectId(book_id)})
        if book:
            book['_id'] = serialize_id(book['_id'])
            # Convert backslashes to forward slashes in cover_image path
            if book.get('cover_image'):
                book['cover_image'] = book['cover_image'].replace('\\', '/')
            return render_template("edit_book.html", book=book)
        return render_template("books.html", books=list(db.books.find()), error="Book not found")
    except Exception as e:
        print(f"Error in get_book: {str(e)}")
        return render_template("books.html", books=list(db.books.find()), error=str(e))

@app.route('/api/books/<book_id>', methods=['GET'])
def api_get_book(book_id):
    try:
        book = db.books.find_one({'_id': ObjectId(book_id)})
        if book:
            book['_id'] = serialize_id(book['_id'])
            return jsonify(book)
        return jsonify({"error": "Book not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/adminDashboard.html")
@login_required
def admin_dashboard_template():
    return render_template("adminDashboard.html")

@app.route("/user-dashboard")
@login_required
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    try:
        # Get user's information
        user = db.users.find_one({'userId': session.get('user_id')})
        if not user:
            return redirect(url_for('login'))
        
        # Get user's borrowed books (both current and returned)
        borrowed_books = list(db.borrowed_books.find({
            'user_id': session.get('user_id')
        }).sort('borrowed_date', -1))  # Sort by most recent first
        
        # Convert ObjectId to string for borrowed books
        for book in borrowed_books:
            book['_id'] = str(book['_id'])
            book['book_id'] = str(book['book_id'])
            # Format dates for display
            book['borrowed_date'] = book['borrowed_date'].strftime('%Y-%m-%d')
            book['return_date'] = book['return_date'].strftime('%Y-%m-%d')
            if 'returned_date' in book:
                book['returned_date'] = book['returned_date'].strftime('%Y-%m-%d')
        
        # Get total available books count
        available_books_count = db.books.count_documents({
            'book_count': {'$gt': {'$ifNull': ['$borrowed_count', 0]}}
        })
        
        # Get total borrowed books count (currently borrowed)
        current_borrowed_count = db.borrowed_books.count_documents({
            'user_id': session.get('user_id'),
            'status': 'borrowed'
        })
        
        # Get total books count
        total_books = db.books.count_documents({})
        
        return render_template("userDashboard.html",
                             user=user,
                             borrowed_books=borrowed_books,
                             available_books_count=available_books_count,
                             current_borrowed_count=current_borrowed_count,
                             total_books=total_books)
    except Exception as e:
        print(f"Error in user dashboard: {str(e)}")
        return render_template("userDashboard.html",
                             user={'total_penalty': 0},
                             borrowed_books=[],
                             available_books_count=0,
                             current_borrowed_count=0,
                             total_books=0,
                             error=str(e))

@app.route("/staff-dashboard")
@login_required
def staff_dashboard():
    if session.get('role') != 'staff':
        return redirect(url_for('login'))
    try:
        # Get counts for dashboard
        users_count = db.users.count_documents({'role': 'user'})
        books_count = db.books.count_documents({})
        
        # Get recently added books (last 5)
        recent_books = list(db.books.find().sort('created_at', -1).limit(5))
        for book in recent_books:
            book['_id'] = str(book['_id'])
            if book.get('cover_image'):
                book['cover_image'] = book['cover_image'].replace('\\', '/')
        
        return render_template("staffDashboard.html",
                             users_count=users_count,
                             books_count=books_count,
                             recent_books=recent_books)
    except Exception as e:
        print(f"Error in staff dashboard: {str(e)}")
        return render_template("staffDashboard.html",
                             users_count=0,
                             books_count=0,
                             recent_books=[],
                             error=str(e))

@app.route("/lend-book", methods=['GET', 'POST'])
@login_required
def lend_book():
    if request.method == 'GET':
        try:
            # Get all books that have available copies
            books = list(db.books.find())
            books = [{**book, '_id': serialize_id(book['_id'])} for book in books]
            # Convert backslashes to forward slashes in cover_image paths
            for book in books:
                if book.get('cover_image'):
                    book['cover_image'] = book['cover_image'].replace('\\', '/')
            return render_template("lend_books.html", books=books)
        except Exception as e:
            print(f"Error in lend_book: {str(e)}")
            return render_template("lend_books.html", books=[], error=str(e))
    
    elif request.method == 'POST':
        try:
            book_id = request.form.get('book_id')
            user_id = request.form.get('user_id')
            return_date = datetime.strptime(request.form.get('return_date'), '%Y-%m-%d')
            
            # Get the book details
            book = db.books.find_one({'_id': ObjectId(book_id)})
            if not book:
                return render_template("lend_books.html", books=list(db.books.find()), error="Book not found")
            
            # Check if user exists
            user = db.users.find_one({'userId': user_id})
            if not user:
                return render_template("lend_books.html", books=list(db.books.find()), error="User not found")
            
            # Check if book has available copies
            if book['book_count'] <= book.get('borrowed_count', 0):
                return render_template("lend_books.html", books=list(db.books.find()), error="No copies available")
            
            # Create borrowed book record
            borrowed_book = {
                'book_id': book_id,
                'user_id': user_id,
                'book_title': book['title'],
                'author': book['author'],
                'isbn': book['isbn'],
                'department': book['department'],
                'borrowed_date': datetime.now(),
                'return_date': return_date,
                'status': 'borrowed'
            }
            
            # Insert into borrowed_books collection
            db.borrowed_books.insert_one(borrowed_book)
            
            # Update book's borrowed count
            db.books.update_one(
                {'_id': ObjectId(book_id)},
                {'$inc': {'borrowed_count': 1}}
            )
            
            # Send email notification
            email_subject = "Book Borrowed Successfully"
            email_body = f"""
            <h2>Book Borrowed</h2>
            <p>Dear {user['name']},</p>
            <p>You have successfully borrowed the following book:</p>
            <ul>
                <li><strong>Title:</strong> {book['title']}</li>
                <li><strong>Author:</strong> {book['author']}</li>
                <li><strong>ISBN:</strong> {book['isbn']}</li>
                <li><strong>Return Date:</strong> {return_date.strftime('%Y-%m-%d')}</li>
            </ul>
            <p>Please return the book by the specified return date.</p>
            <p>Best regards,<br>Library Management System Team</p>
            """
            send_email(email_subject, email_body, user['email'])
            
            # Get updated list of books
            books = list(db.books.find())
            books = [{**book, '_id': serialize_id(book['_id'])} for book in books]
            for book in books:
                if book.get('cover_image'):
                    book['cover_image'] = book['cover_image'].replace('\\', '/')
            
            return render_template("lend_books.html", books=books, message="Book lent successfully!")
            
        except Exception as e:
            print(f"Error in lend_book POST: {str(e)}")
            return render_template("lend_books.html", books=list(db.books.find()), error=str(e))

@app.route("/borrowed-books")
@login_required
def borrowed_books():
    try:
        # Get filter parameters
        status = request.args.get('status')
        user_id = request.args.get('user_id')
        
        # Build query
        query = {}
        if status:
            query['status'] = status
        if user_id:
            query['user_id'] = user_id
        
        # Get filtered borrowed books
        borrowed_books = list(db.borrowed_books.find(query))
        borrowed_books = [{**book, '_id': serialize_id(book['_id'])} for book in borrowed_books]
        
        # Get user names for each borrowed book
        for book in borrowed_books:
            user = db.users.find_one({'userId': book['user_id']})
            if user:
                book['user_name'] = user.get('name', 'Unknown User')
            else:
                book['user_name'] = 'Unknown User'
        
        return render_template("borrowed_books.html", borrowed_books=borrowed_books)
    except Exception as e:
        print(f"Error in borrowed_books: {str(e)}")
        return render_template("borrowed_books.html", borrowed_books=[], error=str(e))

@app.route("/return-book/<book_id>", methods=['POST'])
@login_required
def return_book(book_id):
    try:
        # Get the borrowed book record
        borrowed_book = db.borrowed_books.find_one({'_id': ObjectId(book_id)})
        if not borrowed_book:
            return redirect(url_for('borrowed_books', error="Borrowed book record not found"))
        
        # Calculate days difference and penalty
        current_date = datetime.now()
        return_date = borrowed_book['return_date']
        days_difference = (current_date - return_date).days
        penalty = 0
        
        if days_difference > 0:
            penalty = days_difference * 5  # Rs. 5 per day penalty
        
        # Update the borrowed book status and add penalty information
        update_data = {
            'status': 'returned',
            'returned_date': current_date,
            'days_late': days_difference if days_difference > 0 else 0,
            'penalty_amount': penalty
        }
        
        db.borrowed_books.update_one(
            {'_id': ObjectId(book_id)},
            {'$set': update_data}
        )
        
        # Decrease the borrowed count in the books collection
        db.books.update_one(
            {'_id': ObjectId(borrowed_book['book_id'])},
            {'$inc': {'borrowed_count': -1}}
        )
        
        # Get user details and update penalty in user record
        user = db.users.find_one({'userId': borrowed_book['user_id']})
        if user:
            # Update user's total penalty
            db.users.update_one(
                {'userId': borrowed_book['user_id']},
                {'$inc': {'total_penalty': penalty}}
            )
            
            # Send email notification with penalty information
            email_subject = "Book Returned Successfully"
            email_body = f"""
            <h2>Book Returned</h2>
            <p>Dear {user.get('name', 'User')},</p>
            <p>The following book has been marked as returned:</p>
            <ul>
                <li><strong>Title:</strong> {borrowed_book['book_title']}</li>
                <li><strong>Author:</strong> {borrowed_book['author']}</li>
                <li><strong>ISBN:</strong> {borrowed_book['isbn']}</li>
                <li><strong>Due Date:</strong> {return_date.strftime('%Y-%m-%d')}</li>
                <li><strong>Returned Date:</strong> {current_date.strftime('%Y-%m-%d')}</li>
            </ul>
            """
            
            if penalty > 0:
                email_body += f"""
                <p><strong>Late Return Penalty:</strong></p>
                <ul>
                    <li>Days Late: {days_difference}</li>
                    <li>Penalty Amount: Rs. {penalty}</li>
                </ul>
                <p>Please pay the penalty amount at the library counter.</p>
                """
            
            email_body += """
            <p>Thank you for returning the book!</p>
            <p>Best regards,<br>Library Management System Team</p>
            """
            
            send_email(email_subject, email_body, user.get('email'))
        
        return redirect(url_for('borrowed_books', message="Book returned successfully!"))
    except Exception as e:
        print(f"Error in return_book: {str(e)}")
        return redirect(url_for('borrowed_books', error=str(e)))

@app.route("/available-books", methods=['GET'])
@login_required
def available_books():
    try:
        # Get filter parameters
        department = request.args.get('department')
        search = request.args.get('search')
        
        # Build query
        query = {}
        if department:
            query['department'] = department
            
        if search:
            query['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'author': {'$regex': search, '$options': 'i'}},
                {'isbn': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get books from database
        books = list(db.books.find(query))
        
        # Convert ObjectId to string and process cover images
        for book in books:
            book['_id'] = str(book['_id'])
            if book.get('cover_image'):
                book['cover_image'] = book['cover_image'].replace('\\', '/')
        
        # Get unique departments for filter dropdown
        departments = sorted(db.books.distinct('department'))
        
        # Get total books count
        total_books = db.books.count_documents({})
        
        return render_template("available_books.html",
                             books=books,
                             departments=departments,
                             total_books=total_books)
    except Exception as e:
        print(f"Error in available_books: {str(e)}")
        return render_template("available_books.html",
                             books=[],
                             departments=[],
                             total_books=0,
                             error=str(e))

if __name__ == '__main__':
    app.run(debug=True, port=5432,host='0.0.0.0') 