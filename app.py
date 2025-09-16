from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ----------- App Setup -----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'segreta'

# Ensure DB is in the same folder as this script
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------- User Model -----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

# ----------- Routes -----------
@app.route('/')
def home():
    return render_template("home.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template("signup.html")

    data = request.get_json() or request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({'message': 'All fields are required'}), 400

    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        print(f"[SUCCESS] User added: {username} ({email})")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Could not add user: {e}")
        return jsonify({'message': 'Database error'}), 500

    # Show all users in console for verification
    users = User.query.all()
    print("Current users in DB:")
    for u in users:
        print(f"{u.id} | {u.username} | {u.email}")

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")

    data = request.get_json() or request.form
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({'message': 'Both email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    session['user_id'] = user.id
    return jsonify({'message': 'Logged in successfully'}), 200

# ----------- List all users (for debugging) -----------
@app.route('/users')
def list_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email} for u in users])

# ----------- Initialize Database -----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create DB if it doesn't exist
        print(f"[INFO] Database path: {db_path}")

    app.run(debug=True, host='0.0.0.0', port=5000)
