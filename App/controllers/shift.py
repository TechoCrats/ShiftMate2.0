from App.models import Shift, Attendance
from App.database import db
from datetime import date, timedelta, time as dtime

def schedule_shift(user_id: int, work_date: date, start: dtime, end: dtime, role=None, location=None):
    existing = Shift.query.filter_by(
        user_id=user_id,
        work_date=work_date,
        start_time=start,
        end_time=end
    ).first()
    if existing:
        if role is not None: existing.role = role
        if location is not None: existing.location = location
        db.session.commit()
        return existing

    shift = Shift(
        user_id=user_id,
        work_date=work_date,
        start_time=start,
        end_time=end,
        role=role,
        location=location
    )
    db.session.add(shift)
    db.session.commit()

    # Ensure attendance exists
    att = Attendance.query.filter_by(shift_id=shift.id, user_id=user_id).first()
    if not att:
        db.session.add(Attendance(shift_id=shift.id, user_id=user_id))
        db.session.commit()

    return shift

def schedule_week(user_id: int, week_start: date, daily_windows: dict, role=None, location=None, skip_existing=True):
    created, skipped = [], []
    for offset in range(7):
        pair = daily_windows.get(offset) or daily_windows.get(str(offset))
        if not pair:
            continue
        start_s, end_s = pair
        start = dtime.fromisoformat(start_s)
        end   = dtime.fromisoformat(end_s)
        work_day = week_start + timedelta(days=offset)

        existing = Shift.query.filter_by(
            user_id=user_id,
            work_date=work_day,
            start_time=start,
            end_time=end
        ).first()

        if existing:
            if skip_existing:
                if role is not None: existing.role = role
                if location is not None: existing.location = location
                db.session.commit()
                skipped.append(existing)
                continue
            else:
                raise ValueError("Duplicate shift exists")

        created.append(
            schedule_shift(user_id, work_day, start, end, role, location)
        )

    return {
        "created": [s.get_json() for s in created],
        "skipped": [s.get_json() for s in skipped]
    }

def get_roster(start_date: date, end_date: date):
    q = Shift.query.filter(Shift.work_date.between(start_date, end_date))\
                   .order_by(Shift.work_date.asc(), Shift.start_time.asc())
    return [s.get_json() for s in q.all()]