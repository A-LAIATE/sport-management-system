from app.models import Roles
from app.utils import get_user_by_username, create_user


def test_get_user_by_valid_username(client):
    """
    GIVEN a valid username
    WHEN the user is returned
    THEN check that the returned value is a User with the correct username
    """
    assert get_user_by_username("test").username == "test"


def test_get_user_by_invalid_username(client):
    """
    GIVEN an invalid username
    WHEN the function returns a value
    THEN check that the value is None
    """
    assert get_user_by_username("invalid_username") is None


def test_create_user(client):
    """
    GIVEN a set of new user details
    WHEN the user is created
    THEN check that the details are correct
    """
    user = create_user("new@mail.com", "new_user", "hashed_password")
    assert user.username == "new_user"
    assert user.email == "new@mail.com"
    assert user.password == "hashed_password"
    assert user.role is Roles.CUSTOMER

    user = create_user("nottaken@mail.com", "new_user", "hashed_password_again")
    assert user is None

    user = create_user("new@mail.com", "new_user", "hashed_password_again")
    assert user is None


def test_create_user_with_role(client):
    """
    GIVEN a set of new user details including a role
    WHEN the user is created
    THEN check that the details are correct
    """
    user = create_user("user@mail.com", "new_user", "hashed_password", Roles.ADMIN)
    assert user.email == "user@mail.com"
    assert user.username == "new_user"
    assert user.password == "hashed_password"
    assert user.role is Roles.ADMIN
