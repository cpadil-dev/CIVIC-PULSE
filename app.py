import os
import base64
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

# Configure SQLite database and upload folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'civicpulse.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================

class Issue(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    agency = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Reported')  # Reported, Under Review, In Progress, Resolved
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    ward = db.Column(db.String(150), nullable=False)
    location_text = db.Column(db.String(250))
    description = db.Column(db.Text)
    photo = db.Column(db.Text)          # Base64 or image URL
    after_photo = db.Column(db.Text)    # Resolution proof photo
    upvotes = db.Column(db.Integer, default=1)
    created_at = db.Column(db.String(50), default=lambda: datetime.utcnow().isoformat())
    admin_note = db.Column(db.Text, default='')
    reported_by = db.Column(db.String(100), default='Anonymous Citizen')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'agency': self.agency,
            'severity': self.severity,
            'status': self.status,
            'lat': self.lat,
            'lng': self.lng,
            'ward': self.ward,
            'locationText': self.location_text,
            'description': self.description,
            'photo': self.photo,
            'afterPhoto': self.after_photo,
            'upvotes': self.upvotes,
            'createdAt': self.created_at,
            'adminNote': self.admin_note,
            'reportedBy': self.reported_by
        }


class CitizenUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), unique=True, nullable=False)
    points = db.Column(db.Integer, default=250)

    def to_dict(self):
        return {
            'name': self.name,
            'contact': self.contact,
            'points': self.points
        }


# ==========================================
# INITIALIZE SEED DATA (UPDATED FOR FLASK 3+)
# ==========================================
with app.app_context():
    db.create_all()
    if not Issue.query.first():
        seed_issue = Issue(
            id='CP-101',
            title='Deep Pothole near Old Bus Stand Junction',
            category='Roads & Potholes',
            agency='PWD - Public Works Dept',
            severity='High',
            status='Reported',
            lat=11.6052,
            lng=75.5921,
            ward='Ward 1: Old Bus Stand Junction',
            location_text='Old Bus Stand Junction, Vadakara',
            description='Large crater near bus bay entrance causing traffic backlog[cite: 1].',
            photo='https://images.unsplash.com/photo-1515162816999-a0c47dc192f8?w=400',
            upvotes=18,
            reported_by='Rahul Kumar'
        )
        db.session.add(seed_issue)
        db.session.commit()


# ==========================================
# API ENDPOINTS
# ==========================================

@app.route('/api/issues', methods=['GET'])
def get_issues():
    """Retrieve all civic defect reports."""
    issues = Issue.query.order_by(Issue.created_at.desc()).all()
    return jsonify([i.to_dict() for i in issues])


@app.route('/api/issues', methods=['POST'])
def create_issue():
    """Submit a new civic defect report with auto-routing[cite: 1]."""
    data = request.json
    
    # Generate unique issue ID
    issue_count = Issue.query.count()
    new_id = f"CP-{102 + issue_count}"

    new_issue = Issue(
        id=new_id,
        title=data.get('title'),
        category=data.get('category'),
        agency=data.get('agency', 'PWD - Public Works Dept'),
        severity=data.get('severity', 'Medium'),
        status='Reported',
        lat=float(data.get('lat', 11.6083)),
        lng=float(data.get('lng', 75.5918)),
        ward=data.get('ward', 'Ward 6: Town Hall Ward'),
        location_text=data.get('locationText', ''),
        description=data.get('description', ''),
        photo=data.get('photo', ''),
        upvotes=1,
        reported_by=data.get('reportedBy', 'Citizen')
    )

    db.session.add(new_issue)
    db.session.commit()
    return jsonify({"success": True, "issue": new_issue.to_dict()}), 201


@app.route('/api/issues/<issue_id>/upvote', methods=['POST'])
def upvote_issue(issue_id):
    """Upvote an existing issue to increase community visibility[cite: 1]."""
    issue = Issue.query.get(issue_id)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404
    
    issue.upvotes += 1
    db.session.commit()
    return jsonify({"success": True, "upvotes": issue.upvotes})


@app.route('/api/issues/<issue_id>/admin', methods=['PUT'])
def update_issue_admin(issue_id):
    """Agency admin endpoint to update status, reassign department, or add resolution proof[cite: 1]."""
    issue = Issue.query.get(issue_id)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404

    data = request.json
    issue.status = data.get('status', issue.status)
    issue.agency = data.get('agency', issue.agency)
    issue.admin_note = data.get('adminNote', issue.admin_note)
    if data.get('afterPhoto'):
        issue.after_photo = data.get('afterPhoto')

    db.session.commit()
    return jsonify({"success": True, "issue": issue.to_dict()})


@app.route('/api/citizen/login', methods=['POST'])
def citizen_login():
    """Register or login citizen session."""
    data = request.json
    contact = data.get('contact')
    name = data.get('name')

    user = CitizenUser.query.filter_by(contact=contact).first()
    if not user:
        user = CitizenUser(name=name, contact=contact, points=250)
        db.session.add(user)
        db.session.commit()

    return jsonify({"success": True, "user": user.to_dict()})


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Authenticate agency administrator."""
    data = request.json
    if data.get('email') == 'admin@vadakara.gov.in' and data.get('password') == 'admin123':
        return jsonify({"success": True, "token": "mock-jwt-admin-token"})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)