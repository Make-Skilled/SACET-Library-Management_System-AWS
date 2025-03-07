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
        total_books = sum(book.get('book_count', 0) for book in db.books.find())
        borrowed_count = sum(1 for book in db.books.find() if book.get('borrowed_count', 0) > 0)
        
        # Get recent activities
        recent_activities = [
            {
                'description': 'New book added: "The Great Gatsby"',
                'timestamp': '2 minutes ago'
            },
            {
                'description': 'User "John Doe" borrowed "1984"',
                'timestamp': '15 minutes ago'
            },
            {
                'description': 'New user registered: "Jane Smith"',
                'timestamp': '1 hour ago'
            },
            {
                'description': 'Book "To Kill a Mockingbird" returned',
                'timestamp': '2 hours ago'
            }
        ]
        
        return render_template("adminDashboard.html",
                             users_count=users_count,
                             books_count=books_count,
                             borrowed_count=borrowed_count,
                             recent_activities=recent_activities)
    except Exception as e:
        print(f"Error in admin dashboard: {str(e)}")
        return render_template("adminDashboard.html",
                             users_count=0,
                             books_count=0,
                             borrowed_count=0,
                             recent_activities=[],
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

@app.route("/users")
@login_required
def users():
    try:
        users = list(db.users.find())
        users = [{**user, '_id': serialize_id(user['_id'])} for user in users]
        return render_template("users.html", users=users)
    except Exception as e:
        print(f"Error in users page: {str(e)}")
        return render_template("users.html", users=[], error=str(e))

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

@app.route("/books")
@login_required
def books():
    try:
        books = list(db.books.find())
        books = [{**book, '_id': serialize_id(book['_id'])} for book in books]
        # Convert backslashes to forward slashes in cover_image paths
        for book in books:
            if book.get('cover_image'):
                book['cover_image'] = book['cover_image'].replace('\\', '/')
        return render_template("books.html", books=books)
    except Exception as e:
        print(f"Error in books page: {str(e)}")
        return render_template("books.html", books=[], error=str(e))

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
            return redirect('/api/users')
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
        # Get user's borrowed books
        user_id = session.get('user_id')
        borrowed_books = list(db.books.find({'borrowed_by': user_id}))
        
        # Get available books
        available_books = list(db.books.find({
            'book_count': {'$gt': {'$ifNull': ['$borrowed_count', 0]}}
        }))
        
        return render_template("userDashboard.html",
                             borrowed_books=borrowed_books,
                             available_books=available_books)
    except Exception as e:
        print(f"Error in user dashboard: {str(e)}")
        return render_template("userDashboard.html",
                             borrowed_books=[],
                             available_books=[],
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
        borrowed_count = sum(1 for book in db.books.find() if book.get('borrowed_count', 0) > 0)
        
        # Get recent activities
        recent_activities = list(db.activities.find().sort('timestamp', -1).limit(5))
        
        return render_template("staffDashboard.html",
                             users_count=users_count,
                             books_count=books_count,
                             borrowed_count=borrowed_count,
                             recent_activities=recent_activities)
    except Exception as e:
        print(f"Error in staff dashboard: {str(e)}")
        return render_template("staffDashboard.html",
                             users_count=0,
                             books_count=0,
                             borrowed_count=0,
                             recent_activities=[],
                             error=str(e))

if __name__ == '__main__':
    app.run(debug=True, port=5432) 