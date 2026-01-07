import pytest
from flask_login import current_user
from app.models import Roles
from app.utils import get_user_by_username, verify_credentials


def test_signup_page(client):
    """
    GIVEN a get request to the signup page
    WHEN a response is returned
    THEN check that the request was successful
    """
    assert client.get("/auth/signup").status_code == 200


def test_signup_user_creation(client):
    """
    GIVEN valid username and password
    WHEN a new user is created
    THEN check that the user gets logged in, and that their password is hashed"""
    with client:
        client.post(
            "/auth/signup",
            data={
                "email": "test1@mail.com",
                "username": "test1",
                "password": "test2password",
                "confirm": "test2password",
            },
        )

        user = get_user_by_username("test1")
        assert user.username == "test1"
        assert user.email == "test1@mail.com"
        assert user.password != "test2"
        assert user.role == Roles.CUSTOMER


@pytest.mark.parametrize(
    ("email", "username", "password", "confirm", "redirect"),
    (
        ("", "", "", "", "/auth/signup"),  # Invalid Inputs
        (
            "test@mail.com",
            "test",
            "testpassword",
            "testpassword",
            "/auth/signup",
        ),  # Existing User
        (
            "notanemail",
            "testing1",
            "password",
            "password",
            "/auth/signup",
        ),  # Invalid email
        ("an@email", "testing2", "shortpw", "shortpw", "/auth/signup"),  # Too short p/w
        (
            "an@email",
            "testing2",
            "toolong" * 2000,
            "toolong" * 2000,
            "/auth/signup",
        ),  # Too long p/w
        (
            "new@mail.com",
            "testing3",
            "password",
            "password",
            "/customer/",
        ),  # Valid Input
        (
            "new@mail.com",
            "testing3",
            "password",
            "notpassword",
            "/auth/signup",
        ),  # confirm does not match password
    ),
)
def test_signup_validation(client, email, username, password, confirm, redirect):
    """
    GIVEN a set of sign up credentials, and a destination
    WHEN a response is returned
    THEN check that the user is redirected to the correct page
    """
    response = client.post(
        "/auth/signup",
        data={
            "email": email,
            "username": username,
            "password": password,
            "confirm": confirm,
        },
        follow_redirects=True,
    )
    assert response.request.path == redirect


def test_login_page(client):
    """
    GIVEN a get request to the login page
    WHEN a response is returned
    THEN check that the request was successful
    """
    assert client.get("/auth/login").status_code == 200


def test_valid_login(client):
    """
    GIVEN valid login credentials
    WHEN the user is logged in
    THEN check that the current_user is properly set
    """
    with client:
        client.post(
            "/auth/login", data={"identifier": "test", "password": "testpassword"}
        )

        assert current_user.username == "test"

        client.post(
            "/auth/login",
            data={"identifier": "test@mail.com", "password": "testpassword"},
        )

        assert current_user.username == "test"


@pytest.mark.parametrize(
    ("username", "password", "redirect"),
    (
        ("", "", "/auth/login"),  # Invalid Inputs
        ("test@mail.com", "testpassword", "/customer/"),  # Existing User with email
        ("test", "testpassword", "/customer/"),  # Existing User with username
        ("test", "wrongpassword", "/auth/login"),  # Existing User with username
        ("test@mail.com", "wrongpassword", "/auth/login"),  # Existing User with email
        ("test1", "toolong" * 2000, "/auth/login"),  # Too long p/w
    ),
)
def test_login_validation(client, username, password, redirect):
    """
    GIVEN a set of login credentials, and a destination
    WHEN a response is returned
    THEN check that the user is redirected to the correct page
    """
    with client:
        response = client.post(
            "/auth/login",
            data={"identifier": username, "password": password},
            follow_redirects=True,
        )

        assert response.request.path == redirect


def test_verify_credentials_func(client):
    """
    GIVEN a set of credentials
    WHEN they are being verified
    THEN they should return
    """

    # Valid identifiers
    assert verify_credentials("test", "testpassword") is not None
    assert verify_credentials("test@mail.com", "testpassword") is not None

    # Invalid identifiers
    assert verify_credentials("wrong", "testpassword") is None
    assert verify_credentials("wrong@mail.com", "testpassword") is None

    # Invalid ident and password
    assert verify_credentials("wrong", "wrongpassword") is None
    assert verify_credentials("wrong@mail.com", "wrongpassword") is None

    # Invalid password
    assert verify_credentials("test", "wrongpassword") is None
    assert verify_credentials("test@mail.com", "wrongpassword") is None
