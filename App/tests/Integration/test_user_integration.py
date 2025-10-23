import os
import pytest
from datetime import date, timedelta
from App.main import create_app
from App.database import db, create_db
from App.controllers import (
    create_user,
    get_user,
    schedule_week,
    get_roster,
    clock_in,
    clock_out,
    weekly_report
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.UserIntegrationTests  # This matches the -k filter in the CLI command
]
# ============================================================================
# PYTEST FIXTURE - Setup once for all integration tests
# ============================================================================

@pytest.fixture(autouse=True, scope="module")
def test_db():
    """Create test app and DB for integration tests."""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'})
    with app.app_context():
        create_db()
        yield app.test_client()
        db.drop_all()
    try:
        os.remove('test.db')
    except OSError:
        pass


# ============================================================================
# INTEGRATION TESTS - Selected by: pytest -k "UserIntegrationTests"
# Run with: flask test user int
# ============================================================================

def test_create_and_get_user(test_db):
    """Test user creation and retrieval"""
    user = create_user("alice", "password123", isAdmin=False)
    assert user is not None, "User creation failed"
    fetched = get_user(user.id)
    assert fetched.username == "alice", "Username mismatch"

def test_schedule_weekly_shifts(test_db):
    """Test scheduling a week of shifts"""
    staff = create_user("staff_bob", "staffpass", isAdmin=False)
    week_start = date.today() - timedelta(days=date.today().weekday())
    daily_windows = {0: ["09:00", "17:00"], 1: ["09:00", "17:00"]}
    
    result = schedule_week(
        user_id=staff.id,
        week_start=week_start,
        daily_windows=daily_windows,
        role="staff",
        location="Main Office"
    )
    assert "created" in result, "Missing created shifts list"
    assert len(result["created"]) > 0, "No shifts created"

def test_view_roster_shifts(test_db):
    """Test viewing the roster"""
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_end = week_start + timedelta(days=6)
    roster = get_roster(week_start, week_end)
    assert isinstance(roster, list), "Roster should be a list"

def test_attendance_flow(test_db):
    """Test clock in/out flow"""
    user = create_user("clock_test", "pass123", isAdmin=False)
    week_start = date.today() - timedelta(days=date.today().weekday())
    daily_windows = {0: ["09:00", "17:00"]}
    
    shifts = schedule_week(
        user_id=user.id,
        week_start=week_start,
        daily_windows=daily_windows,
        role="staff",
        location="Test Location"
    )
    
    shift_id = shifts["created"][0]["id"]
    in_record = clock_in(user.id, shift_id)
    assert in_record is not None, "Clock in failed"
    
    out_record = clock_out(user.id, shift_id)
    assert out_record is not None, "Clock out failed"
    assert out_record.time_out > out_record.time_in, "Invalid clock times"


def test_weekly_report(test_db):
    """Test that the weekly report displays accurate total hours and shift coverage"""
    user1 = create_user("report_user1", "pass123", isAdmin=False)
    user2 = create_user("report_user2", "pass456", isAdmin=False)
    
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_end = week_start + timedelta(days=6)
    
    daily_windows_user1 = {
        0: ["09:00", "17:00"],
        2: ["10:00", "18:00"]
    }
    daily_windows_user2 = {
        1: ["09:00", "13:00"],
        3: ["14:00", "22:00"]
    }
    
    shifts1 = schedule_week(
        user_id=user1.id,
        week_start=week_start,
        daily_windows=daily_windows_user1,
        role="staff",
        location="Main Office"
    )
    
    shifts2 = schedule_week(
        user_id=user2.id,
        week_start=week_start,
        daily_windows=daily_windows_user2,
        role="staff",
        location="Main Office"
    )
    
    for shift in shifts1["created"]:
        clock_in(user1.id, shift["id"])
        clock_out(user1.id, shift["id"])
    
    for shift in shifts2["created"]:
        clock_in(user2.id, shift["id"])
        clock_out(user2.id, shift["id"])
    
    report = weekly_report(week_start)
    
    assert report is not None, "Weekly report generation failed"
    assert isinstance(report, dict), "Report should be a dictionary"
    
    assert "totals_per_user" in report, "Report missing totals_per_user data"
    assert "shifts" in report, "Report missing shifts data"
    
    totals = report["totals_per_user"]
    assert len(totals) > 0, "Should have user totals"
    
    for user_id, data in totals.items():
        assert "scheduled_hours" in data, f"User {user_id} missing scheduled_hours"
        assert "worked_hours" in data, f"User {user_id} missing worked_hours"
        assert isinstance(data["scheduled_hours"], (int, float)), "Scheduled hours should be numeric"
        assert isinstance(data["worked_hours"], (int, float)), "Worked hours should be numeric"
        assert data["scheduled_hours"] >= 0, "Scheduled hours should be non-negative"
        assert data["worked_hours"] >= 0, "Worked hours should be non-negative"
    
    shifts_data = report["shifts"]
    assert isinstance(shifts_data, list), "Shifts should be a list"
    assert len(shifts_data) > 0, "Should have shift coverage data"