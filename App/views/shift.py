from flask import Blueprint, request, jsonify, render_template
from App.controllers import schedule_shift, schedule_week, get_roster
from App.models import Shift, User
from App.database import db

shift_views = Blueprint('shift_views', __name__)

# ==================== WEB ROUTES ====================

@shift_views.route('/shifts', methods=['GET'])
def shifts_page():
    """Render the main shifts management page"""
    return render_template('shifts.html')

@shift_views.route('/roster', methods=['GET'])
def roster_page():
    """Render the roster calendar view"""
    return render_template('roster.html')

# ==================== API ROUTES ====================

@shift_views.route('/api/shifts', methods=['POST'])
def create_shift():
    """Create a single shift — thin view that delegates to controller"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # delegate parsing/validation to controller
    shift = schedule_shift(
        user_id=data.get('user_id'),
        work_date=data.get('work_date'),
        start=data.get('start_time'),
        end=data.get('end_time'),
        role=data.get('role'),
        location=data.get('location')
    )

    # assume controller returns a Shift instance or dict-like result
    if hasattr(shift, 'get_json'):
        return jsonify({"message": "Shift created", "shift": shift.get_json()}), 201
    return jsonify({"message": "Shift created", "result": shift}), 201


@shift_views.route('/api/shifts/week', methods=['POST'])
def create_week_schedule():
    """Schedule a week of shifts — thin view delegating to controller"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    result = schedule_week(
        user_id=data.get('user_id'),
        week_start=data.get('week_start'),
        daily_windows=data.get('daily_windows'),
        role=data.get('role'),
        location=data.get('location'),
        skip_existing=data.get('skip_existing', True)
    )

    return jsonify({"message": "Week scheduled", "result": result}), 201


@shift_views.route('/api/roster', methods=['GET'])
def get_roster_api():
    """Get roster for a date range — delegate to controller"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    roster = get_roster(start_date, end_date)
    return jsonify({
        "start_date": start_date,
        "end_date": end_date,
        "shifts": roster,
        "count": len(roster) if roster is not None else 0
    }), 200


@shift_views.route('/api/shifts/<int:shift_id>', methods=['GET'])
def get_shift(shift_id):
    """Get a single shift by ID"""
    shift = Shift.query.get(shift_id)
    if not shift:
        return jsonify({"error": "Shift not found"}), 404
    return jsonify(shift.get_json()), 200


@shift_views.route('/api/shifts/<int:shift_id>', methods=['PUT'])
def update_shift(shift_id):
    """Update a shift — minimal view, model handles validation"""
    shift = Shift.query.get(shift_id)
    if not shift:
        return jsonify({"error": "Shift not found"}), 404

    data = request.get_json() or {}

    # assign values directly; assume model or controller enforces types/constraints
    if 'work_date' in data:
        shift.work_date = data['work_date']
    if 'start_time' in data:
        shift.start_time = data['start_time']
    if 'end_time' in data:
        shift.end_time = data['end_time']
    if 'role' in data:
        shift.role = data['role']
    if 'location' in data:
        shift.location = data['location']

    db.session.commit()
    return jsonify({"message": "Shift updated", "shift": shift.get_json()}), 200


@shift_views.route('/api/shifts/<int:shift_id>', methods=['DELETE'])
def delete_shift(shift_id):
    """Delete a shift — simple view"""
    shift = Shift.query.get(shift_id)
    if not shift:
        return jsonify({"error": "Shift not found"}), 404

    db.session.delete(shift)
    db.session.commit()
    return jsonify({"message": "Shift deleted"}), 200


@shift_views.route('/api/users/<int:user_id>/shifts', methods=['GET'])
def get_user_shifts(user_id):
    """Get all shifts for a specific user — minimal filtering in view"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    query = Shift.query.filter_by(user_id=user_id)

    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')

    if start_str:
        query = query.filter(Shift.work_date >= start_str)
    if end_str:
        query = query.filter(Shift.work_date <= end_str)

    shifts = query.order_by(Shift.work_date.asc(), Shift.start_time.asc()).all()
    return jsonify({
        "user_id": user_id,
        "username": user.username,
        "shifts": [s.get_json() for s in shifts],
        "count": len(shifts)
    }), 200


@shift_views.route('/api/shifts/summary', methods=['GET'])
def get_shifts_summary():
    """Get summary statistics — view delegates filtering to model/query and summarises minimal info"""
    query = Shift.query

    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)

    if start_str:
        query = query.filter(Shift.work_date >= start_str)
    if end_str:
        query = query.filter(Shift.work_date <= end_str)
    if user_id:
        query = query.filter_by(user_id=user_id)

    shifts = query.all()

    total_hours = sum(getattr(s, 'duration_hours', lambda: 0)() for s in shifts)
    unique_users = len(set(s.user_id for s in shifts))
    shifts_by_location = {}
    shifts_by_role = {}

    for shift in shifts:
        if shift.location:
            shifts_by_location[shift.location] = shifts_by_location.get(shift.location, 0) + 1
        if shift.role:
            shifts_by_role[shift.role] = shifts_by_role.get(shift.role, 0) + 1

    return jsonify({
        "total_shifts": len(shifts),
        "total_hours": round(total_hours, 2),
        "unique_users": unique_users,
        "shifts_by_location": shifts_by_location,
        "shifts_by_role": shifts_by_role
    }), 200