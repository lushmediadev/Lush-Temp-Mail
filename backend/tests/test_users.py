from backend.app import db
from backend.app.config import settings


def setup_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "users.db")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "admin-pass")
    monkeypatch.setattr(settings, "user_username", "user")
    monkeypatch.setattr(settings, "user_password", "user-pass")
    db.init_db()


def test_init_db_seeds_admin_and_user_accounts(monkeypatch, tmp_path):
    setup_temp_db(monkeypatch, tmp_path)

    users = db.list_users()

    assert [(item["username"], item["role"]) for item in users] == [
        ("admin", "admin"),
        ("user", "user"),
    ]
    assert db.authenticate_user("admin", "admin-pass")["role"] == "admin"
    assert db.authenticate_user("user", "user-pass")["role"] == "user"
    assert db.authenticate_user("user", "wrong") is None


def test_user_password_can_be_updated_without_exposing_hash(monkeypatch, tmp_path):
    setup_temp_db(monkeypatch, tmp_path)
    user = db.create_user(username="editor", password="old-pass", role="user")

    updated = db.update_user(user["id"], username="editor2", password="new-pass", role="admin")

    assert updated["username"] == "editor2"
    assert updated["role"] == "admin"
    assert "password_hash" not in updated
    assert db.authenticate_user("editor", "old-pass") is None
    assert db.authenticate_user("editor2", "new-pass")["role"] == "admin"
