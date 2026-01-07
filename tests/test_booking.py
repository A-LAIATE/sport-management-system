from app.models import Session, User
from app import db
from sqlalchemy import select


def test_cancel_session(login_client):
    """
    GIVEN that a user is booked on a session
    WHEN the user cancels their attendance
    THEN only that users attendance to the sessions is effcted
    """
    user = db.session.execute(select(User).where(User.user_id == 100)).scalar()
    session = db.session.execute(
        select(Session).where(Session.session_id == 100)
    ).scalar()
    assert session is not None
    assert user is not None

    with login_client(user=user) as client:
        r = client.post("customer/delete_session/100")
        assert r.status_code == 302

        assert len(user.sessions) == 0
        session = db.session.execute(
            select(Session).where(Session.session_id == 100)
        ).scalar()
        assert session is not None
        assert session.users[0].user_id == 101
