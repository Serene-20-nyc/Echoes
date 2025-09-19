from flask import Flask, flash, request, jsonify, session, redirect, url_for, render_template
import random
import smtplib
import secrets
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production-' + os.urandom(24).hex())

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def is_demo_mode() -> bool:
    """Check if we're in demo mode (bypasses email verification)."""
    return os.environ.get('DEMO_MODE', 'true').lower() == 'true'

def is_email_verified(email: str) -> bool:
    """Check if the given email has a valid verified record."""
    if not email:
        return False
    
    # In demo mode, consider all emails verified
    if is_demo_mode():
        return True
        
    latest = EmailVerification.query.filter_by(email=email, verified=True).order_by(EmailVerification.created_at.desc()).first()
    return latest is not None

# User model
# This model is used to store user credentials in the database
# username is a unique identifier for the user
# email is a unique identifier for the user and is used for authentication
# password is the hashed password for the user

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationship with secrets
    secrets = db.relationship('Secret', backref='author', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Secret model for storing user messages/secrets
class Secret(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'is_anonymous': self.is_anonymous,
            'created_at': self.created_at.isoformat(),
            'author': 'Anonymous' if self.is_anonymous else self.author.username
        }

# Password Reset model for secure token management
class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    token = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    def is_expired(self):
        return datetime.datetime.now(datetime.UTC) > self.expires_at
    
    def is_valid(self):
        return not self.used and not self.is_expired()

# Email Verification model
class EmailVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)

    def is_expired(self):
        return datetime.datetime.now(datetime.UTC) > self.expires_at

    def is_valid(self, submitted_code: str):
        return (not self.verified) and (not self.is_expired()) and (self.code == submitted_code)

def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_email(recipient_email, subject, html_body, text_body=None):
    """Enhanced email sending function with HTML support and dev fallback."""
    # Configuration
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    sender_email = os.environ.get('SENDER_EMAIL', 'your_email@example.com')
    sender_password = os.environ.get('SENDER_PASSWORD', 'your_password')
    flask_env = os.environ.get('FLASK_ENV', 'production').lower()
    dev_mode_flag = os.environ.get('EMAIL_DEV_MODE', 'true').lower() == 'true'

    # Auto-enable dev fallback if clearly not configured
    creds_incomplete = (not sender_email or sender_email.endswith('@example.com') or sender_password in (None, '', 'your_password', 'your_app_password_here'))
    dev_mode = dev_mode_flag or flask_env == 'development' or creds_incomplete

    print(f"[EMAIL] Email config - Dev mode: {dev_mode}, SMTP: {smtp_server}:{smtp_port}, From: {sender_email}")

    # Construct message (for both paths)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"Segreta <{sender_email}>"
    msg['To'] = recipient_email

    if text_body:
        text_part = MIMEText(text_body, 'plain', 'utf-8')
        msg.attach(text_part)

    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(html_part)

    if dev_mode:
        print("\n======= EMAIL (DEV MODE) =======")
        print(f"To: {recipient_email}")
        print(f"Subject: {subject}")
        if text_body:
            print("\n-- Text body --\n" + text_body)
        print("\n-- HTML body (truncated) --\n" + html_body[:500] + ('...' if len(html_body) > 500 else ''))
        print("======= END EMAIL =======\n")
        return True

    try:
        print(f"[EMAIL] Attempting to send email via {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)  # Enable debug output
        server.starttls()
        print(f"[AUTH] Logging in as {sender_email}")
        server.login(sender_email, sender_password)
        print(f"[EMAIL] Sending email to {recipient_email}")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] Email sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] SMTP Authentication failed: {e}")
        print("[INFO] For Gmail, make sure you're using an App Password, not your regular password")
        print("[INFO] Enable 2-Step Verification and generate an App Password at: https://myaccount.google.com/apppasswords")
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP Error: {e}")
    except Exception as e:
        print(f"[ERROR] Email sending failed: {e}")
    
    # Fallback: print to console to unblock local testing
    print("\n======= EMAIL (FALLBACK PRINT) =======")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    if text_body:
        print("\n-- Text body --\n" + text_body)
    print("\n-- HTML body (truncated) --\n" + html_body[:500] + ('...' if len(html_body) > 500 else ''))
    print("======= END EMAIL =======\n")
    return False

def send_verification_email(recipient_email, code):
    subject = "Your Verification Code - Segreta"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
        <h2 style="text-align: center; margin-bottom: 30px;">Segreta Verification</h2>
        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 8px; text-align: center;">
            <p>Hello beautiful soul!</p>
            <p>Your verification code is:</p>
            <h1 style="font-size: 2.5em; letter-spacing: 5px; margin: 20px 0; color: #FFD700;">{code}</h1>
            <p>Enter this code on the site to verify your email.</p>
        </div>
        <p style="text-align: center; margin-top: 20px; font-style: italic;">
            Echoes of Love Team [SUCCESS]
        </p>
    </div>
    """
    text_body = f"Hello Beautiful Soul\n\nYour verification code is: {code}\n\nEnter this on the site to verify your email.\n\nEchoes of Love Team [SUCCESS]"
    return send_email(recipient_email, subject, html_body, text_body)

def generate_reset_token():
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)

def send_password_reset_email(recipient_email, reset_token):
    """Send password reset email with secure token"""
    reset_url = f"{request.url_root}reset-password?token={reset_token}"
    subject = "Reset Your Password - Segreta"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
        <h2 style="text-align: center; margin-bottom: 30px;">Password Reset - Segreta</h2>
        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 8px;">
            <p>Hello beautiful soul!</p>
            <p>You requested to reset your password for your Segreta account. Click the button below to create a new password:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: #FFD700; color: #333; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">
                    Reset My Password
                </a>
            </div>
            <p style="font-size: 0.9em; color: #ccc;">
                If the button doesn't work, copy and paste this link into your browser:<br>
                <span style="word-break: break-all;">{reset_url}</span>
            </p>
            <p style="font-size: 0.8em; color: #ccc; margin-top: 20px;">
                This link will expire in 1 hour for security reasons. If you didn't request this reset, please ignore this email.
            </p>
        </div>
        <p style="text-align: center; margin-top: 20px; font-style: italic;">
            Echoes of Love Team [SUCCESS]
        </p>
    </div>
    """
    
    text_body = f"""
    Hello Beautiful Soul

    You requested to reset your password for your Segreta account.
    
    Please visit this link to reset your password:
    {reset_url}
    
    This link will expire in 1 hour for security reasons.
    If you didn't request this reset, please ignore this email.
    
    Echoes of Love Team [SUCCESS]
    """
    
    return send_email(recipient_email, subject, html_body, text_body)

@app.route('/verify', methods=['GET'])
def verify_page():
    """Render the email verification page. Email comes from session or query param."""
    email = request.args.get('email') or session.get('email_to_verify')
    if not email:
        flash('Please provide an email to verify.')
        return redirect(url_for('signup_page'))
    return render_template('verify.html', email=email)

@app.route('/send-code', methods=['POST'])
def send_code():
    """Send a 6-digit verification code to the provided email and persist it."""
    # Accept both form POST and JSON
    email = request.form.get('email') if request.form else None
    if not email and request.is_json:
        payload = request.get_json(silent=True) or {}
        email = payload.get('email')

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    # Basic email format check
    import re
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'message': 'Please enter a valid email address'}), 400

    # Generate code and store
    code = generate_verification_code()
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)

    # Cleanup previous unverified records for this email
    EmailVerification.query.filter(
        EmailVerification.email == email,
        EmailVerification.verified == False
    ).delete()

    record = EmailVerification(email=email, code=code, expires_at=expires_at)
    db.session.add(record)
    db.session.commit()

    # Send the email
    send_verification_email(email, code)

    # Keep for UX navigations
    session['email_to_verify'] = email

    # If request came from a form, render the verify page; if AJAX/JSON, return JSON
    if request.is_json:
        return jsonify({'message': 'Verification code sent. Please check your inbox.'}), 200
    return render_template('verify.html', email=email)

@app.route('/verify-email', methods=['POST'])
def verify_email():
    """Validate the submitted code against the database and mark verified."""
    code = request.form.get('code') if request.form else None
    email = session.get('email_to_verify') or request.form.get('email')
    if not (email and code):
        flash('Missing email or code.')
        return redirect(url_for('verify_page'))

    latest = EmailVerification.query.filter_by(email=email).order_by(EmailVerification.created_at.desc()).first()
    if not latest or not latest.is_valid(code):
        flash('Invalid or expired code. Please try again or resend a new code.')
        return redirect(url_for('verify_page', email=email))

    latest.verified = True
    db.session.commit()

    flash("Email verified successfully!")
    return redirect(url_for('dashboard'))

@app.route('/resend-code', methods=['GET'])
def resend_code():
    email = request.args.get('email') or session.get('email_to_verify')
    if not email:
        flash('No email to resend code for.')
        return redirect(url_for('signup_page'))

    print(f"[RESEND] Resending code to {email}")

    # Rate limit: only once per minute
    recent = EmailVerification.query.filter(
        EmailVerification.email == email,
        EmailVerification.created_at > datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=1)
    ).first()
    if recent:
        flash('A code was sent recently. Please wait a minute before requesting another.')
        return redirect(url_for('verify_page', email=email))

    try:
        # Clean up old codes
        EmailVerification.query.filter(
            EmailVerification.email == email,
            EmailVerification.verified == False
        ).delete()
        
        code = generate_verification_code()
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
        record = EmailVerification(email=email, code=code, expires_at=expires_at)
        db.session.add(record)
        db.session.commit()
        
        print(f"[EMAIL] Resending verification code {code} to {email}")
        email_sent = send_verification_email(email, code)
        
        if email_sent:
            flash('A new verification code has been sent to your email.')
        else:
            flash('A new verification code has been generated. Check your console (dev mode).')
            
    except Exception as e:
        print(f"[ERROR] Error resending code: {e}")
        flash('There was an error sending the verification code. Please try again.')

    return redirect(url_for('verify_page', email=email))

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template("signup.html")

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({'message': 'Whispers of identity, contact, and secret must all be present'}), 400

    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists!'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    # Trigger email verification flow (skip in demo mode)
    if not is_demo_mode():
        try:
            code = generate_verification_code()
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
            
            # Remove any previous unverified records
            EmailVerification.query.filter(
                EmailVerification.email == email,
                EmailVerification.verified == False
            ).delete()
            
            verification = EmailVerification(email=email, code=code, expires_at=expires_at)
            db.session.add(verification)
            db.session.commit()
            
            print(f"[EMAIL] Sending signup verification code {code} to {email}")
            email_sent = send_verification_email(email, code)
            session['email_to_verify'] = email
            
            if email_sent:
                message = 'User created successfully! We have sent a verification code to your email.'
            else:
                message = 'User created successfully! Check your console for the verification code (dev mode).'
                
            return jsonify({
                'message': message,
                'user': {
                    'username': new_user.username,
                    'email': new_user.email
                },
                'redirect_url': url_for('verify_page', email=email)
            }), 201
            
        except Exception as e:
            print(f"[ERROR] Error sending signup verification: {e}")
            return jsonify({
                'message': 'User created successfully! There was an issue sending the verification code. You can request a new one.',
                'user': {
                    'username': new_user.username,
                    'email': new_user.email
                },
                'redirect_url': url_for('verify_page', email=email)
            }), 201
    else:
        # Demo mode - no verification needed
        print(f"[SUCCESS] Demo mode - user {new_user.username} created without verification")
        return jsonify({
            'message': 'User created successfully! (Demo mode - no verification needed)',
            'user': {
                'username': new_user.username,
                'email': new_user.email
            }
        }), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({'message': 'Both email and secret must be present'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials!'}), 401

    # Enforce verified email before login (skip in demo mode)
    if not is_email_verified(user.email):
        print(f"[LOGIN] Login blocked - email not verified for {user.email}")
        session['email_to_verify'] = user.email
        
        # Always send a new verification code when login is attempted
        try:
            # Clean up old unverified codes
            EmailVerification.query.filter(
                EmailVerification.email == user.email,
                EmailVerification.verified == False
            ).delete()
            
            # Generate and send new verification code
            code = generate_verification_code()
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)
            
            verification = EmailVerification(email=user.email, code=code, expires_at=expires_at)
            db.session.add(verification)
            db.session.commit()
            
            print(f"[EMAIL] Sending verification code {code} to {user.email}")
            email_sent = send_verification_email(user.email, code)
            
            if email_sent:
                message = 'Please verify your email before logging in. We have sent you a verification code.'
            else:
                message = 'Please verify your email before logging in. Check your console for the verification code (dev mode).'
                
        except Exception as e:
            print(f"[ERROR] Error sending verification code: {e}")
            message = 'Please verify your email before logging in. There was an issue sending the code.'
        
        return jsonify({
            'message': message,
            'redirect_url': url_for('verify_page', email=user.email)
        }), 403

    session['user_id'] = user.id
    return jsonify({'message': 'Logged in successfully!'}), 200

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    verified = is_email_verified(user.email)
    return render_template('dashboard.html', user=user, is_verified=verified)

@app.route('/api/secrets', methods=['GET'])
def get_secrets():
    secrets = Secret.query.order_by(Secret.created_at.desc()).all()
    return jsonify([secret.to_dict() for secret in secrets])

@app.route('/api/secrets', methods=['POST'])
def create_secret():
    print(f"[DEBUG] Create secret called - Session: {session}")
    
    if 'user_id' not in session:
        print("[ERROR] No user_id in session")
        return jsonify({'message': 'Please log in first'}), 401
    
    data = request.get_json()
    print(f"[DATA] Received data: {data}")
    
    title = data.get('title') if data else None
    content = data.get('content') if data else None
    is_anonymous = data.get('is_anonymous', False) if data else False
    
    if not all([title, content]):
        print(f"[ERROR] Missing data - Title: {title}, Content: {content}")
        return jsonify({'message': 'Title and content are required'}), 400
    
    # Get user
    user = User.query.get(session['user_id'])
    if not user:
        print(f"[ERROR] User not found for ID: {session['user_id']}")
        return jsonify({'message': 'User not found'}), 404
    
    print(f"[USER] User: {user.username} ({user.email})")
    
    # Check email verification (skip in demo mode)
    if not is_email_verified(user.email):
        print(f"[EMAIL] Email verification check - Demo mode: {is_demo_mode()}, Verified: {is_email_verified(user.email)}")
        if not is_demo_mode():
            return jsonify({'message': 'Please verify your email before posting secrets.'}), 403
        else:
            print("[SUCCESS] Demo mode - skipping email verification")

    try:
        secret = Secret(
            title=title,
            content=content,
            is_anonymous=is_anonymous,
            user_id=session['user_id']
        )
        
        db.session.add(secret)
        db.session.commit()
        
        print(f"[SUCCESS] Secret created successfully: {secret.id}")
        
        return jsonify({
            'message': 'Secret shared successfully!',
            'secret': secret.to_dict()
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        db.session.rollback()
        return jsonify({'message': 'Failed to save secret. Please try again.'}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.errorhandler(404)
def handle_404(e):
    # Handle Chrome DevTools requests gracefully
    if '/.well-known/appspecific/com.chrome.devtools' in request.path:
        return jsonify({'message': 'Chrome DevTools endpoint not available'}), 404
    return jsonify({'message': 'Page not found'}), 404

@app.errorhandler(500)
def handle_500(e):
    # Return JSON for API requests, HTML for regular requests
    if request.path.startswith('/api/') or request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
        return jsonify({'message': 'Internal server error. Please try again.'}), 500
    return render_template('error.html', error='Internal Server Error'), 500

# Password Reset Routes
@app.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'message': 'Email is required'}), 400
    
    # Basic email validation
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'message': 'Please enter a valid email address'}), 400
    
    # Rate limiting: Check for recent reset requests
    recent_reset = PasswordReset.query.filter(
        PasswordReset.email == email,
        PasswordReset.created_at > datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
    ).first()
    
    if recent_reset:
        return jsonify({'message': 'A password reset email was already sent recently. Please check your email or wait 5 minutes before requesting another.'}), 429
    
    # Check if user exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return jsonify({'message': 'If an account with this email exists, you will receive a password reset link shortly.'}), 200
    
    # Clean up old reset tokens for this email (older than 5 minutes)
    PasswordReset.query.filter(
        PasswordReset.email == email,
        PasswordReset.created_at <= datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
    ).delete()
    
    # Generate new reset token
    reset_token = generate_reset_token()
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
    
    # Save reset token to database
    password_reset = PasswordReset(
        email=email,
        token=reset_token,
        expires_at=expires_at
    )
    db.session.add(password_reset)
    db.session.commit()
    
    # Send reset email
    if send_password_reset_email(email, reset_token):
        return jsonify({'message': 'If an account with this email exists, you will receive a password reset link shortly.'}), 200
    else:
        return jsonify({'message': 'Failed to send reset email. Please try again later.'}), 500

@app.route('/reset-password', methods=['GET'])
def reset_password_page():
    token = request.args.get('token')
    if not token:
        flash('Invalid or missing reset token.')
        return redirect(url_for('forgot_password_page'))
    
    # Verify token
    reset_request = PasswordReset.query.filter_by(token=token).first()
    if not reset_request or not reset_request.is_valid():
        flash('Invalid or expired reset token.')
        return redirect(url_for('forgot_password_page'))
    
    return render_template('reset_password.html', token=token)

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not all([token, new_password, confirm_password]):
        return jsonify({'message': 'All fields are required'}), 400
    
    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400
    
    if len(new_password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters long'}), 400
    
    # Verify token
    reset_request = PasswordReset.query.filter_by(token=token).first()
    if not reset_request or not reset_request.is_valid():
        return jsonify({'message': 'Invalid or expired reset token'}), 400
    
    # Find user and update password
    user = User.query.filter_by(email=reset_request.email).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Update password
    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    
    # Mark reset token as used
    reset_request.used = True
    
    db.session.commit()
    
    return jsonify({'message': 'Password reset successfully! You can now log in with your new password.'}), 200

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/api/questions')
def get_quiz_questions():
    """Return quiz questions for the cosmic flower personality test"""
    questions = [
        {
            "q": "What draws you most to a garden?",
            "opts": ["The vibrant colors that dance in sunlight", "The peaceful silence and gentle breeze", "The sweet fragrance that fills the air", "The intricate patterns of petals and leaves"]
        },
        {
            "q": "How do you express love?",
            "opts": ["Through passionate gestures and bold declarations", "With quiet acts of care and devotion", "By creating beautiful moments and memories", "Through deep conversations and understanding"]
        },
        {
            "q": "What time of day speaks to your soul?",
            "opts": ["Golden sunrise full of new possibilities", "Peaceful twilight with gentle shadows", "Starlit midnight with cosmic mysteries", "Bright noon with clear, focused energy"]
        },
        {
            "q": "In relationships, you value most:",
            "opts": ["Excitement and adventure together", "Comfort and emotional safety", "Beauty and romantic gestures", "Intellectual connection and growth"]
        },
        {
            "q": "Your ideal way to spend a quiet evening:",
            "opts": ["Dancing under the stars", "Reading by candlelight", "Creating art or music", "Deep conversation with someone special"]
        }
    ]
    return jsonify(questions)

@app.route('/api/gemini', methods=['POST'])
def cosmic_flower_match():
    """AI-powered flower personality matching based on quiz answers"""
    data = request.get_json()
    answers = data.get('answers', [])
    
    # Simple personality matching logic (can be enhanced with actual AI later)
    flower_matches = {
        'passionate': {
            'flower': 'Cosmic Rose 🌹',
            'description': 'Like a rose that blooms boldly in the cosmic garden, you radiate passion and intensity. Your love burns bright like a supernova, drawing others into your gravitational pull. You express emotions with the fierce beauty of stellar fire, creating moments that echo through eternity.'
        },
        'peaceful': {
            'flower': 'Moonlight Lily 🌙',
            'description': 'Gentle as moonbeams dancing on still water, you embody serene beauty and quiet strength. Like a lily that blooms in the soft glow of starlight, you bring peace to turbulent hearts. Your love is a sanctuary, a cosmic haven where souls find rest.'
        },
        'creative': {
            'flower': 'Nebula Orchid 🌺',
            'description': 'Rare and exquisite like an orchid born from cosmic dust, you see beauty in the extraordinary. Your creative spirit paints love in colors that don\'t exist on Earth. You transform ordinary moments into masterpieces that sparkle across the universe.'
        },
        'thoughtful': {
            'flower': 'Wisdom Lotus 🪷',
            'description': 'Rising from cosmic waters with profound grace, you embody the lotus of enlightenment. Your love grows from deep understanding and spiritual connection. Like ancient starlight, your wisdom illuminates the path for others seeking truth in the vast cosmos.'
        }
    }
    
    # Analyze answers to determine personality type
    passionate_count = sum(1 for ans in answers if 'passionate' in ans.lower() or 'bold' in ans.lower() or 'dance' in ans.lower() or 'adventure' in ans.lower())
    peaceful_count = sum(1 for ans in answers if 'peaceful' in ans.lower() or 'quiet' in ans.lower() or 'gentle' in ans.lower() or 'safety' in ans.lower())
    creative_count = sum(1 for ans in answers if 'beautiful' in ans.lower() or 'art' in ans.lower() or 'romantic' in ans.lower() or 'creating' in ans.lower())
    thoughtful_count = sum(1 for ans in answers if 'conversation' in ans.lower() or 'understanding' in ans.lower() or 'intellectual' in ans.lower() or 'reading' in ans.lower())
    
    # Determine dominant personality
    scores = {
        'passionate': passionate_count,
        'peaceful': peaceful_count, 
        'creative': creative_count,
        'thoughtful': thoughtful_count
    }
    
    dominant_type = max(scores.keys(), key=lambda k: scores[k])
    result = flower_matches[dominant_type]
    
    return jsonify({
        'text': f"<h3>{result['flower']}</h3><p>{result['description']}</p><br><p><em>Your cosmic essence resonates with the frequency of {result['flower'].lower()}, a rare bloom in the infinite garden of the universe.</em></p>"
    })

# Create demo data
def create_demo_data():
    """Create engaging demo content for hackathon presentation"""
    if Secret.query.count() == 0:  # Only create if no secrets exist
        # Create multiple demo users
        demo_users = [
            {
                'username': 'CosmicDreamer',
                'email': 'demo@segreta.com',
                'password': 'demo123'
            },
            {
                'username': 'StarWhisperer',
                'email': 'star@segreta.com', 
                'password': 'demo123'
            },
            {
                'username': 'MoonlightPoet',
                'email': 'moon@segreta.com',
                'password': 'demo123'
            }
        ]
        
        created_users = []
        for user_data in demo_users:
            existing_user = User.query.filter_by(username=user_data['username']).first()
            if not existing_user:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=generate_password_hash(user_data['password'], method='pbkdf2:sha256')
                )
                db.session.add(user)
                created_users.append(user)
            else:
                created_users.append(existing_user)
        
        db.session.commit()
        
        # Create diverse and engaging demo secrets
        demo_secrets = [
            {
                'title': 'A Cosmic Love Letter',
                'content': 'To the stars above, I whisper my deepest feelings. In this vast universe, love finds a way to connect two souls across infinite space. Every constellation tells our story.',
                'is_anonymous': True,
                'user_idx': 0
            },
            {
                'title': 'Dreams of Tomorrow',
                'content': 'Sometimes I dream of a world where kindness is the universal language, where every heart beats in harmony with the cosmos. What if we could make this dream reality?',
                'is_anonymous': False,
                'user_idx': 0
            },
            {
                'title': 'Midnight Confessions',
                'content': 'At 3 AM, when the world sleeps, I find myself talking to the moon about hopes, fears, and the beautiful mystery of existence. The silence holds all my secrets.',
                'is_anonymous': True,
                'user_idx': 1
            },
            {
                'title': 'Finding Light in Darkness',
                'content': 'After months of feeling lost, I finally found my spark again. It was in the smallest things - morning coffee, a friend\'s laugh, the way sunlight dances through leaves.',
                'is_anonymous': False,
                'user_idx': 1
            },
            {
                'title': 'Secret Garden of the Heart',
                'content': 'I have a secret garden in my heart where I keep all the beautiful moments. Every sunset, every kind word, every gentle touch grows there like flowers in eternal spring.',
                'is_anonymous': True,
                'user_idx': 2
            },
            {
                'title': 'The Courage to Be Vulnerable',
                'content': 'Today I learned that vulnerability isn\'t weakness - it\'s the birthplace of love, belonging, and joy. Sharing our authentic selves is the most beautiful gift we can give.',
                'is_anonymous': False,
                'user_idx': 2
            },
            {
                'title': 'Whispers to the Universe',
                'content': 'Dear Universe, thank you for every broken road that led me here, every storm that made me stronger, every star that guided me home to myself.',
                'is_anonymous': True,
                'user_idx': 0
            },
            {
                'title': 'Love in the Time of Digital',
                'content': 'In a world of screens and notifications, I still believe in handwritten letters, long conversations under stars, and love that transcends pixels and WiFi.',
                'is_anonymous': False,
                'user_idx': 1
            }
        ]
        
        # Add demo secrets
        for secret_data in demo_secrets:
            user = created_users[secret_data['user_idx']]
            secret = Secret(
                title=secret_data['title'],
                content=secret_data['content'],
                is_anonymous=secret_data['is_anonymous'],
                user_id=user.id
            )
            db.session.add(secret)
        
        db.session.commit()
        print('[SUCCESS] Demo data created successfully!')
        print('[DATA] Demo users created:')
        for user in created_users:
            print(f'   - {user.username} (email: {user.email}, password: demo123)')
        print('[READY] Ready for hackathon presentation!')

# Create the database
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Ensure existing SQLite DBs have required columns
        try:
            cols = db.session.execute(text("PRAGMA table_info(user)")).fetchall()
            col_names = {row[1] for row in cols}
            if 'created_at' not in col_names:
                db.session.execute(text("ALTER TABLE user ADD COLUMN created_at DATETIME"))
                db.session.commit()
                print("[MIGRATION] Added 'created_at' column to user table")
        except Exception as e:
            print(f"[MIGRATION] Skipped schema check or migration failed: {e}")
        create_demo_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')


