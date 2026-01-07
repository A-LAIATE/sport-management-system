from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask import session as flask_session
from flask_login import current_user, logout_user
from app.utils import (
    requires_role,
    verify_password,
    update_password,
    update_email,
    update_username,
)
from app.models import Roles, Session, User
from app import db, stripe
from sqlalchemy import select
from app.forms import ActivitySelectForm, UpdateUserDetailsForm
from app.booking_utils import (
    CalanderItem,
    get_facility,
    get_facility_attendance,
    session_expired,
    get_users_next_sessions,
    group_session_list_by_day,
)
from werkzeug.urls import url_parse
from stripe import error
import datetime
import json


customer = Blueprint(
    "customer",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/customer",
)


@customer.route("/")
@requires_role(Roles.CUSTOMER)
def index():
    upcoming_sessions = get_users_next_sessions()
    grouped = group_session_list_by_day(upcoming_sessions)

    # grouped is not ordered so to display in chrono.
    #  order we use the sorted keys to access the dict.
    keys = sorted(grouped.keys())

    return render_template("dashboard.html", upcoming_sessions=grouped, keys=keys)


@customer.route("/membership")
@requires_role(Roles.CUSTOMER)
def membership():
    return render_template("membership.html")


@customer.route("/booking", methods=["GET", "POST"])
@requires_role(Roles.CUSTOMER)
def booking():
    form = ActivitySelectForm()
    sessions = None

    if form.validate_on_submit():
        c = CalanderItem(form.date.data, type=form.type.data)
        sessions = c.generate_overview()

        # Remove any sessions the user has already booked.
        sessions = [s for s in sessions if s not in flask_session["booked_sessions"]]
        return render_template("session_booking.html", form=form, activities=sessions)

    return render_template("session_booking.html", form=form)


@customer.route("/save_session", methods=["GET", "POST"])
@requires_role(Roles.CUSTOMER)
def save_session():
    request.form.items()

    sessions = list(request.form.items())

    # Save provisionally booked sessions.
    flask_session["booked_sessions"] += [
        sess[1] for sess in sessions if sess[1] not in flask_session["booked_sessions"]
    ]
    flask_session.modified = True
    flash("Added to basket", "success")

    return redirect(url_for("customer.booking"))


@customer.route("/manage_sessions")
@requires_role(Roles.CUSTOMER)
def manage_sessions():
    sessions = current_user.sessions

    sessions = [
        (sess, True) if session_expired(sess) else (sess, False) for sess in sessions
    ]

    return render_template("session_management.html", sessions=sessions)


@customer.route("/delete_session/<id>", methods=["GET", "POST"])
@requires_role(Roles.CUSTOMER)
def delete_session(id):
    session = db.session.execute(
        select(Session).where(Session.session_id == id)
    ).scalar()

    session.users.remove(current_user)

    # if a session has no attendees then remove it from the db.
    if len(session.users) == 0:
        db.session.delete(session)

    db.session.commit()
    return redirect(url_for("customer.manage_sessions"))


@customer.route("/delete_basket/<id>", methods=["GET", "POST"])
@requires_role(Roles.CUSTOMER)
def delete_basket(id):
    flask_session["booked_sessions"].pop(int(id))
    flask_session.modified = True
    return redirect(url_for("customer.checkout"))


@customer.route("/checkout")
@requires_role(Roles.CUSTOMER)
def checkout():
    sess_objs = []
    valid = True
    for sess in flask_session["booked_sessions"]:
        s = Session.from_unique_code(sess)

        # If a session already exists then use that.
        existing = db.session.execute(
            select(Session).where(
                (Session.start_time == s.start_time)
                & (Session.end_time == s.end_time)
                & (Session.facility_id == s.facility_id)
                & (Session.session_type == s.session_type)
            )
        ).scalar()

        if existing:
            s = existing

        attendance = get_facility_attendance(s)
        facility = get_facility(s)

        if attendance >= facility.max_capacity:
            flash(f" {s} at max capacity", "warning")
            valid = False

        # Provisionally book the user onto the session
        # Not final until db.commit.
        s.users.append(current_user)
        sess_objs.append(s)

        # Don't let user book multiple sessions that start at the same time.
        # The set removes duplicates from the list, if the set has a different length then duplicate start times existed.
        if len(set([s.start_time for s in sess_objs])) != len(sess_objs):
            flash(
                "Timetable clash in selected sessions. You can only attend 1 session per hour",
                "warning",
            )
            valid = False

        start_times = [s.start_time for s in sess_objs]
        # Show an alert for any timetable clashes.
        for dupe in {time for time in start_times if start_times.count(time) > 1}:
            flash(
                f"Time table clash at  {dupe}. Please resolve before payment", "warning"
            )
            valid = False
    # return flask_session["booked_sessions"]
    return render_template("basket.html", sessions=sess_objs, valid=valid)


# @customer.route("/") // if possible, want to preprocess today's available activities without pressing date buttons
@customer.route("/get_sessions")
@customer.route("/get_sessions/<data>")
@requires_role(Roles.CUSTOMER)
def get_sessions(data=None):  # data: YYYY-MM-DD-type
    if data is None:
        date = datetime.date.today()
        type = "general"

    else:
        year = int(data.split("-")[0])
        month = int(data.split("-")[1])
        datenum = int(data.split("-")[2])
        date = datetime.date(year, month, datenum)

        type = data.split("-")[3]

    c = CalanderItem(date, type)
    sessions = c.create_JSON_from_activities()
    js = json.loads(sessions)

    return js


@customer.route("/settings", methods=["POST", "GET"])
@requires_role(Roles.CUSTOMER)
def settings():
    form = UpdateUserDetailsForm(
        data={"email": current_user.email, "username": current_user.username}
    )
    if form.validate_on_submit():
        print(request.form)
        # Make sure user has authenticated
        if not verify_password(form.current_password.data):
            flash("Current password invalid", "warning")
            return redirect(url_for("customer.settings"))

        # If a new password has been entered then set it.
        if form.new_password.data:
            update_password(form.new_password.data)

        # Update username if it has changed and is not taken
        if form.username.data != current_user.username:
            if update_username(form.username.data) is None:
                flash("Could not use that username", "warning")
                return redirect(url_for("customer.settings"))

        # Update email if it has changed and is valid + not taken
        if form.email.data != current_user.email:
            if update_email(form.email.data) is None:
                flash("Could not use that email", "warning")
                return redirect(url_for("customer.settings"))

        flash("Updated account", "success")

    return render_template("settings.html", form=form)


@customer.route("/settings/delete_account", methods=["POST", "GET"])
@requires_role(Roles.CUSTOMER)
def delete_account():
    # Make user reauthenticate before deleting
    if request.method == "GET" and url_parse(request.referrer).path != url_for(
        "auth.reauth"
    ):
        flash("Your account will be deleted if you submit this form.", "danger")
        return redirect(url_for("auth.reauth", next=url_for("customer.delete_account")))

    if current_user.stripe_id is not None:
        try:
            stripe.Customer.delete(current_user.stripe_id)
        except error.InvalidRequestError as e:
            print(str(e))

    user_id = current_user.user_id
    logout_user()

    user = db.session.execute(select(User).where(User.user_id == user_id)).scalar()
    db.session.delete(user)
    db.session.commit()
    flash("Account Deleted", "success")

    return redirect(url_for("main.index"))


@customer.route("/settings/payment_info")
@requires_role(Roles.CUSTOMER)
def payment_info():
    customer = None
    if current_user.stripe_id is None:
        customer = stripe.Customer.create(email=current_user.email)
    if customer:
        current_user.stripe_id = customer.id
        db.session.commit()

    portal = None
    try:
        portal = stripe.billing_portal.Session.create(
            customer=current_user.stripe_id,
            return_url=url_for("customer.settings", _external=True),
        )
    except error.InvalidRequestError:
        flash("Could not create billing portal", "warning")

    if portal is not None:
        return redirect(portal.url)

    return redirect(url_for("customer.settings"))
