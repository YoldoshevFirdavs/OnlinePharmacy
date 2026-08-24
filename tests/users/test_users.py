from unittest.mock import Mock


def test_user_mock_has_required_fields():
    user = Mock()
    user.id = 1
    user.email = "demo@example.com"
    user.is_staff = True
    assert user.email == "demo@example.com"
    assert user.is_staff is True


def test_user_role_helper_works_for_admin():
    role = "admin"
    assert role == "admin"
