# Library Management System - Admin Module

A web-based library management system with an admin module for managing users and books.

## Features

- User Management (Add, Edit, Delete, View)
- Book Management (Add, Edit, Delete, View)
- Dashboard with statistics
- Responsive UI using Tailwind CSS
- RESTful API using Flask
- MongoDB database integration

## Prerequisites

- Python 3.7 or higher
- MongoDB installed and running locally
- Node.js and npm (for development)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd library-management
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following content:
```
MONGODB_URI=mongodb://localhost:27017/
```

## Running the Application

1. Start MongoDB:
```bash
# Make sure MongoDB is running on your system
```

2. Start the Flask application:
```bash
python app.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
library-management/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── static/
│   └── js/
│       └── main.js    # Frontend JavaScript
└── templates/
    └── index.html     # Main HTML template
```

## API Endpoints

### Users
- GET /api/users - Get all users
- POST /api/users - Create a new user
- PUT /api/users/<user_id> - Update a user
- DELETE /api/users/<user_id> - Delete a user

### Books
- GET /api/books - Get all books
- POST /api/books - Create a new book
- PUT /api/books/<book_id> - Update a book
- DELETE /api/books/<book_id> - Delete a book

## Technologies Used

- Frontend:
  - HTML5
  - Tailwind CSS
  - JavaScript (ES6+)
- Backend:
  - Flask (Python)
  - MongoDB
  - Flask-CORS

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request #   S A C E T - L i b r a r y - M a n a g e m e n t _ S y s t e m - A W S  
 