from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud.aiplatform.generative_models import GenerativeModel
from google.cloud import aiplatform
from dotenv import load_dotenv
import json
load_dotenv()
import os

# ----------- App Setup -----------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallback_secret")

aiplatform.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("GCP_LOCATION", "us-central1")
)

# Ensure DB is in the same folder as this script
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(db_path)}'
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


model = GenerativeModel("gemini-1.5-flash")

@app.route("/api/questions", methods=["GET"])
def get_questions():
    """Generate 12 cosmic-floral themed personality questions via Gemini"""
    prompt = """
    Generate 12 multiple-choice personality questions.
    - Theme: cosmic, flowers, love, inner echoes.
    - Each question should have exactly 3 options (simple text).
    - Return in JSON format as a list: [{ "q": "...", "opts": ["...", "...", "..."] }]
    """
    response = model.generate_content(prompt)
    try:
        questions = json.loads(response.text)  # Gemini returns JSON-like text
    except json.JSONDecodeError:
        return jsonify({"error": "Could not parse Gemini response as JSON", "raw": response.text}), 500

    return jsonify(questions)

@app.route("/api/gemini", methods=["POST"])
def gemini_personality():
    """Generate flower result from answers"""
    data = request.get_json()
    answers = data.get("answers", [])

    prompt = f"""
    Based on these answers: {answers},
    choose a flower that best matches the person’s cosmic personality.
    Respond with:
    1. Flower name
    2. Why it reflects them
    3. A poetic yet warm historical or cultural background of the flower
    Style: cosmic, lyrical, romantic.
    Length: 2–3 short paragraphs.
    """

    response = model.generate_content(prompt)
    return jsonify({"text": response.text})

# ----------- Initialize Database -----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create DB if it doesn't exist
        print(f"[INFO] Database path: {db_path}")

    app.run(debug=True, host='0.0.0.0', port=5000)
