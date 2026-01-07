from app.models import User, Roles, Membership
from app import db, hasher, stripe
from sqlalchemy import select
from functools import wraps
from flask import request, redirect, url_for, flash
from flask_login import current_user
from argon2.exceptions import VerifyMismatchError
from stripe import error


def update_password(password, user=current_user):
    user.password = hasher.hash(password)
    db.session.commit()


def update_stripe_details(user):
    """
    If the given user has an associated stripe Customer object then update the email for that object.
    """
    customer = None
    try:
        customer = stripe.Customer.retrieve(user.stripe_id)

    except error.InvalidRequestError as e:
        print(str(e))

    if customer:
        stripe.Customer.modify(customer.id, email=user.email)


def update_email(new_email, user=current_user):
    """
    Try to update the given users email.
    Requires that email is not in use and contains an '@'
    Returns the user if update was successful otherwise None
    """
    if get_user_by_email(new_email) is not None:
        return None
    if "@" not in new_email:
        return None

    user.email = new_email
    db.session.commit()

    update_stripe_details(user)

    return user


def update_username(new_username, user=current_user):
    """
    If the new_username is not already in use then update the users username.
    Returns None on failure or the updated user on success.
    """
    if get_user_by_username(new_username) is not None:
        return None

    user.username = new_username
    db.session.commit()

    return user


def verify_password(password, user=current_user):
    try:
        hasher.verify(user.password, password)
        return True
    except VerifyMismatchError as e:
        print(e)
        return False


def verify_credentials(identifier, password):
    """Returns User if given valid credentials else None"""

    user = get_user_by_username(identifier)

    if not user:
        user = get_user_by_email(identifier)
        if not user:
            return None

    if not verify_password(password, user):
        return None

    # if the password is hashed using outdated version of hasher
    if hasher.check_needs_rehash(user.password):
        user.password = hasher.hash(password)
        db.session.commit()

    return user


def get_user_by_username(username):
    """Return user with given username or None"""
    user = db.session.execute(select(User).where(User.username == username)).scalar()
    return user


def get_user_by_email(email):
    """Return user with given email or None"""
    user = db.session.execute(select(User).where(User.email == email)).scalar()
    return user


def get_user_by_stripe_id(stripe_id):
    """
    Return user with given stripe id or None.
    """

    user = db.session.execute(select(User).where(User.stripe_id == stripe_id)).scalar()

    return user


def create_user(email, username, pass_hash, role=Roles.CUSTOMER):
    """Create new User, add to db.

    Returns:
        None: if user already exists
        user: The new user
    """
    # User already exists
    if get_user_by_username(username) is not None:
        return None
    user = User()
    user.email = email
    user.username = username
    user.password = pass_hash
    user.role = role
    user.membership = Membership.NONE

    db.session.add(user)
    db.session.commit()
    return user


def requires_role(role):
    """
    Decorater that ensures the current user is logged in and has the provided role

        params:
            role (Roles): A model.Roles.role

        Returns:
            If user is authorised: allows access to the view.
            If user is not logged: redirects to login with a next=requested view URL parameter.
            If user has incorrect role: redirects to the main index.
            : In both failure cases an appropriate message is flashed.
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.is_anonymous:
                flash("Please sign in first", "info")
                return redirect(url_for("auth.login", next=request.url))
            if current_user.role is not role:
                flash("You do not have permission for this.", "warning")
                return redirect(url_for("main.index"))

            return f(*args, **kwargs)

        return wrapper

    return decorator


def get_delta_hours(start_time, end_time):
    import datetime

    datetime_start = datetime.datetime.combine(datetime.date.today(), start_time)
    datetime_end = datetime.datetime.combine(datetime.date.today(), end_time)
    delta = (datetime_end - datetime_start) / datetime.timedelta(hours=1)

    return delta
