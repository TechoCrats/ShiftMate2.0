# App/api.py
from App.models.user import User
from App import db
from flask import Blueprint, request, jsonify
from datetime import date, datetime, time as dtime
from flask_jwt_extended import jwt_required, create_access_token
from App.controllers import (
    initialize,
    schedule_shift, schedule_week, get_roster,
    clock_in, clock_out, weekly_report, get_all_users_json
)

api = Blueprint('api', __name__, url_prefix='/api')

def parse_date(s): return date.fromisoformat(s)
def parse_datetime(s): return datetime.fromisoformat(s)


#--- Initilization ---
@api.route('/initialize', methods=['POST'])
def api_initialize():
    """
    Initialize the database and seed initial data.
    Only call this in development / local environments.
    """
    try:
        initialize()
        return jsonify({"status": "success", "message": "Database initialized!"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

#--- Get all users ---
@api.route('/users', methods=['GET'])
@jwt_required
def api_get_users():
    users = get_all_users_json()
    return jsonify(users), 200

#--- Signup endpoint (for testing) ---
@api.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"msg": "Invalid input"}), 400

    username = data['username']
    password = data['password']


    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409


    user = User(username=username)
    user.set_password(password)


    db.session.add(user)
    db.session.commit()

    return jsonify({"msg": "User created successfully"}), 201

#--- Login endpoint (for testing) ---
@api.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401

    # Create JWT token
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200


# --- Admin: create one shift ---
@api.route('/admin/shifts', methods=['POST'])
def api_create_shift():
    data = request.get_json() or {}
    shift = schedule_shift(
        user_id=int(data['user_id']),
        work_date=parse_date(data['date']),
        start=_to_time(data['start']),
        end=_to_time(data['end']),
        role=data.get('role'),
        location=data.get('location'),
    )
    return jsonify(shift.get_json()), 201

# --- Admin: create a week's schedule for a user ---
@api.route('/admin/shifts/bulk', methods=['POST'])
def api_create_week():
    data = request.get_json() or {}
    result = schedule_week(
        user_id=int(data['user_id']),
        week_start=parse_date(data['week_start']),
        daily_windows=data['daily_windows'],
        role=data.get('role'),
        location=data.get('location'),
    )
    return jsonify(result), 201

# --- Staff: combined roster ---
@api.route('/roster', methods=['GET'])
def api_roster():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if not start_str or not end_str:
        return jsonify({
            "error": "Missing 'start' or 'end' query parameters. Expected format: /roster?start=YYYY-MM-DD&end=YYYY-MM-DD"
        }), 400

    try:
        start = parse_date(start_str)
        end = parse_date(end_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    return jsonify(get_roster(start, end)), 200

# --- Staff: time in/out ---
@api.route('/attendance/clock-in', methods=['POST'])
def api_clock_in():
    data = request.get_json() or {}
    att = clock_in(int(data['user_id']), int(data['shift_id']))
    return jsonify(att.get_json()), 200

@api.route('/attendance/clock-out', methods=['POST'])
def api_clock_out():
    data = request.get_json() or {}
    att = clock_out(int(data['user_id']), int(data['shift_id']))
    return jsonify(att.get_json()), 200

# --- Admin: weekly report ---
@api.route('/admin/reports/weekly', methods=['GET'])
def api_weekly_report():
    week_start_str = request.args.get('week_start')
    if not week_start_str:
        return jsonify({"error": "week_start query parameter is required"}), 400
    try:
        week_start = parse_date(week_start_str)
    except ValueError:
        return jsonify({"error": "week_start must be in YYYY-MM-DD format"}), 400

    return jsonify(weekly_report(week_start)), 200

# helpers
def _to_time(s: str) -> dtime:
    return dtime.fromisoformat(s)
