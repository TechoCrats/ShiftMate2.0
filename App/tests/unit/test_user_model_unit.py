import pytest

# Selected by: pytest -k "UserUnitTests"  (and your CLI `flask test user unit`)
class UserUnitTests:

    def test_new_user(self):
        """
        Input:  username='bob', password='bobpass', isAdmin=False
        Expect: username set, isAdmin set; (id is None before DB persist)
        """
        from App.models.user import User  # adjust import path if needed

        user = User(username="bob", password="bobpass", isAdmin=False)

        assert user.username == "bob"
        assert user.isAdmin is False
        # id should be None until added/committed to DB in integration tests
        assert getattr(user, "id", None) is None

    def test_toJSON(self):
        """
        Input:  username='bob', password='bobpass', isAdmin=False
        Expect: get_json() returns {'id': None, 'username': 'bob', 'isAdmin': False}
                and MUST NOT leak password or hash.
        """
        from App.models.user import User

        user = User(username="bob", password="bobpass", isAdmin=False)
        data = user.get_json()

        # core fields
        assert "username" in data and data["username"] == "bob"
        assert "isAdmin" in data and data["isAdmin"] is False

        # before persistence the id is usually None (allow None or missing)
        assert "id" in data  # your get_json() includes id
        assert data["id"] is None

        # security: never expose password fields in JSON
        assert "password" not in data
        assert "password_hash" not in data

    def test_hashed_password(self):
        """
        Input: password='mypass'
        Expect: stored attribute is NOT the raw 'mypass' (hashing via set_password()).
        """
        from App.models.user import User

        user = User(username="alice", password="mypass", isAdmin=False)

        # your model stores the hash in 'password'
        assert hasattr(user, "password")
        assert user.password != "mypass", "Stored password must be a hash, not raw text"

    def test_check_password(self):
        """
        Input: password='mypass'
        Expect: check_password('mypass') is True, check_password('wrong') is False.
        """
        from App.models.user import User

        user = User(username="carol", password="mypass", isAdmin=False)
        assert hasattr(user, "check_password")

        assert user.check_password("mypass") is True
        assert user.check_password("wrong") is False
