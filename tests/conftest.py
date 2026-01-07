import pytest
from app import create_app, db, hasher
from app.models import Roles, Session, Activities, Facilities
import datetime
from flask_login import FlaskLoginClient


# Pytest for flask setup from https://flask.palletsprojects.com/en/2.2.x/testing/
@pytest.fixture()
def app():
    app = create_app(testing=True)
    app.config.update(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "testing"}
    )
    app.test_client_class = FlaskLoginClient

    # Set up
    with app.app_context():
        db.drop_all()
        db.create_all()
        init_test_db()

        yield app

    # Tear down
    with app.app_context():
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login_client(app):
    return app.test_client


def init_test_db():
    from app.models import User

    user = User()
    user.user_id = 100
    user.username = "test"
    user.email = "test@mail.com"
    user.password = hasher.hash("testpassword")
    user.role = Roles.CUSTOMER

    user2 = User()
    user2.user_id = 101
    user2.username = "tester2"
    user2.email = "tester2@mail.com"
    user2.password = hasher.hash("testpassword")
    user2.role = Roles.CUSTOMER

    s1 = Session(
        session_id=100,
        session_type=Activities.SWIMLESSON,
        facility_id=Facilities.POOL,
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(hours=1),
        is_class=0,
    )
    s1.users.append(user)
    s1.users.append(user2)
    db.session.add(user)
    db.session.add(user2)
    db.session.add(s1)
    db.session.commit()
