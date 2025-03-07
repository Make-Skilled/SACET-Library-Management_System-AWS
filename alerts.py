from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.library_db

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

def send_email(subject, body, to_email):
    """Send email using SMTP"""
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

def check_overdue_books():
    """Check for overdue books and send email notifications"""
    try:
        # Get current date
        current_date = datetime.now()
        
        # Find all borrowed books that are overdue
        overdue_books = list(db.borrowed_books.find({
            'status': 'borrowed',
            'return_date': {'$lt': current_date}
        }))
        
        # Group overdue books by user
        user_overdue_books = {}
        for book in overdue_books:
            user_id = book['user_id']
            if user_id not in user_overdue_books:
                user_overdue_books[user_id] = []
            user_overdue_books[user_id].append(book)
        
        # Send email to each user with their overdue books
        for user_id, books in user_overdue_books.items():
            # Get user details
            user = db.users.find_one({'userId': user_id})
            if not user or not user.get('email'):
                continue
            
            # Calculate days overdue for each book
            for book in books:
                days_overdue = (current_date - book['return_date']).days
                book['days_overdue'] = days_overdue
                book['estimated_penalty'] = days_overdue * 5  # Rs. 5 per day penalty
            
            # Prepare email content
            email_subject = "Overdue Books Alert - Library Management System"
            email_body = f"""
            <h2>Overdue Books Alert</h2>
            <p>Dear {user.get('name', 'User')},</p>
            <p>This is a reminder that you have the following overdue books:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <th style="padding: 10px; text-align: left; border: 1px solid #e5e7eb;">Book Title</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #e5e7eb;">Due Date</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #e5e7eb;">Days Overdue</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #e5e7eb;">Estimated Penalty</th>
                </tr>
            """
            
            for book in books:
                email_body += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{book['book_title']}</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{book['return_date'].strftime('%Y-%m-%d')}</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{book['days_overdue']} days</td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">Rs. {book['estimated_penalty']}</td>
                </tr>
                """
            
            email_body += """
            </table>
            <p><strong>Please return these books as soon as possible to avoid additional penalties.</strong></p>
            <p>If you have already returned the books, please ignore this email.</p>
            <p>Best regards,<br>Library Management System Team</p>
            """
            
            # Send email
            send_email(email_subject, email_body, user['email'])
            print(f"Sent overdue alert email to {user['email']}")
        
        return len(overdue_books)
    
    except Exception as e:
        print(f"Error in check_overdue_books: {str(e)}")
        return 0

def run_continuous_check():
    """Run the overdue books check continuously every 5 minutes"""
    print("Starting continuous overdue books check...")
    print("Press Ctrl+C to stop the script")
    
    while True:
        try:
            # Get current time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Checking for overdue books...")
            
            # Run the check
            overdue_count = check_overdue_books()
            print(f"Found {overdue_count} overdue books")
            
            # Wait for 5 minutes before next check
            print("Waiting 5 minutes before next check...")
            time.sleep(300)  # 300 seconds = 5 minutes
            
        except KeyboardInterrupt:
            print("\nStopping the continuous check...")
            break
        except Exception as e:
            print(f"Error in continuous check: {str(e)}")
            print("Waiting 5 minutes before retrying...")
            time.sleep(300)

if __name__ == "__main__":
    run_continuous_check() 