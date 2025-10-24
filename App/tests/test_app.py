import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta
from App.main import create_app
from App.database import db, create_db
from App.models import User
from App.controllers import (
    create_user,
    get_all_users_json,
    login,
    get_user,
    get_user_by_username,
    update_user,
    schedule_week,
    get_roster,
    clock_in,
    clock_out,
    weekly_report
)


LOGGER = logging.getLogger(__name__)

'''
   Unit Tests
'''
class UserUnitTests(unittest.TestCase):

    def test_new_user(self):
        user = User("bob", "bobpass")
        assert user.username == "bob"

    def test_get_json(self):
        user = User("bob", "bobpass")
        user_json = user.get_json()
        self.assertDictEqual(user_json, {"id":None, "username":"bob"})
    
    def test_hashed_password(self):
        password = "mypass"
        hashed = generate_password_hash(password)
        user = User("bob", password)
        assert user.password != password

    def test_check_password(self):
        password = "mypass"
        user = User("bob", password)
        assert user.check_password(password)


# ============================================================
# TEST DATABASE SETUP
# ============================================================
@pytest.fixture(scope="module")
def test_db():
    """Creates a test app + DB for integration tests."""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'})
    with app.app_context():
        create_db()
        yield app.test_client()
        db.drop_all()
    try:
        os.remove("test.db")
    except OSError:
        pass



# ============================================================
# SIMPLE INTEGRATION TESTS
# ============================================================
@pytest.mark.UserIntegrationTests
class TestUserIntegration:
    """Integration tests — real DB + app context."""

    def test_create_and_get_user(self, test_db):
        user = create_user("alice", "password123", isAdmin=False)
        fetched = get_user(user.id)
        assert fetched.username == "alice"

    def test_schedule_weekly_shifts(self, test_db):
        staff = create_user("staff_bob", "staffpass", isAdmin=False)
        week_start = date.today() - timedelta(days=date.today().weekday())
        result = schedule_week(staff.id, week_start, {0: ["09:00", "17:00"]}, "staff", "Main Office")
        assert len(result["created"]) > 0

    def test_view_roster_shifts(self, test_db):
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)
        roster = get_roster(week_start, week_end)
        assert isinstance(roster, list)

    def test_attendance_flow(self, test_db):
        user = create_user("clock_test", "pass123", isAdmin=False)
        week_start = date.today() - timedelta(days=date.today().weekday())
        shifts = schedule_week(user.id, week_start, {0: ["09:00", "17:00"]}, "staff", "Test Location")
        shift_id = shifts["created"][0]["id"]
        assert clock_in(user.id, shift_id)
        assert clock_out(user.id, shift_id)

    def test_weekly_report(self, test_db):
        user = create_user("report_user", "pass123", isAdmin=False)
        week_start = date.today() - timedelta(days=date.today().weekday())
        schedule_week(user.id, week_start, {0: ["09:00", "17:00"]}, "staff", "Main Office")
        report = weekly_report(week_start)
        assert isinstance(report, dict)
        assert "totals_per_user" in report

