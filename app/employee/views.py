from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from app.utils import (
    requires_role,
    get_user_by_email,
    get_user_by_username,
    create_user,
    update_email,
    update_username,
)
from app.booking_utils import (
    CalanderItem,
    get_facility,
    get_facility_attendance,
    session_expired,
)
from app.models import Roles, Session, User
from app.forms import (
    UserSearchForm,
    SignUpForm,
    ActivitySelectForm,
    UpdateUserDetailsForm,
)
from app import db, hasher, stripe
from sqlalchemy import select

employee = Blueprint(
    "employee",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/employee",
)


@employee.route("/ignore", methods=["GET", "POST"])
@requires_role(Roles.EMPLOYEE)
def index_():
    search_form = UserSearchForm()
    signup_form = SignUpForm()

    if search_form.validate_on_submit():
        user = get_user_by_email(search_form.identifier.data)
        if user is None:
            user = get_user_by_username(search_form.identifier.data)
        if user is None:
            flash("Input is not associated with an existing user", "warning")
            return redirect(url_for("employee.index"))

    if signup_form.validate_on_submit():
        return redirect(url_for("employee.index"))

    return render_template(
        "customer_search.html", search_form=search_form, signup_form=signup_form
    )


@employee.route("/", methods=["GET", "POST"])
@requires_role(Roles.EMPLOYEE)
def index():
    search_form = UserSearchForm()
    signup_form = SignUpForm()
    return render_template(
        "customer_search.html", search_form=search_form, signup_form=signup_form
    )


@employee.route("/search", methods=["POST"])
@requires_role(Roles.EMPLOYEE)
def search():
    search_form = UserSearchForm()
    signup_form = SignUpForm()

    if search_form.validate_on_submit():
        user = get_user_by_email(search_form.identifier.data)
        if user is None:
            user = get_user_by_username(search_form.identifier.data)
        if user is None:
            flash("Input is not associated with an existing user", "warning")
        if user.role is not Roles.CUSTOMER:
            flash("Can't login as that user", "warning")
        else:
            # store user_id instead of user object to avoid storing mutable object in session.
            # don't need to worry about out-of-date user object.
            session["customer_id"] = user.user_id
            session["customer_name"] = user.username

            return redirect(url_for("employee.booking"))

    return render_template(
        "customer_search.html", search_form=search_form, signup_form=signup_form
    )


@employee.route("/create", methods=["POST"])
@requires_role(Roles.EMPLOYEE)
def create():
    search_form = UserSearchForm()
    signup_form = SignUpForm()

    if signup_form.validate_on_submit():
        pass_hash = hasher.hash(signup_form.password.data)

        user = create_user(
            email=signup_form.email.data,
            username=signup_form.username.data,
            pass_hash=pass_hash,
            role=Roles.CUSTOMER,
        )
        if user is None:
            flash(
                "Creation Failed. Please try different username and email.", "warning"
            )
            return render_template(
                "customer_search.html", search_form=search_form, signup_form=signup_form
            )

        db.session.add(user)
        db.session.commit()
        flash("Created user", "success")
        # store user_id instead of user object to avoid storing mutable object in session.
        # Safer to trade more db queries.
        session["customer_id"] = user.user_id
        return redirect(url_for("employee.booking"))

    return render_template(
        "customer_search.html", search_form=search_form, signup_form=signup_form
    )


@employee.route("/booking", methods=["GET", "POST"])
@requires_role(Roles.EMPLOYEE)
def booking():
    form = ActivitySelectForm()
    sessions = None

    if form.validate_on_submit():
        c = CalanderItem(form.date.data, type=form.type.data)
        sessions = c.generate_overview()

        # Remove any sessions the user has already booked.
        sessions = [s for s in sessions if s not in session["booked_sessions"]]
        return render_template("booking.html", form=form, activities=sessions)

    return render_template("booking.html", form=form)


@employee.route("/save_session", methods=["GET", "POST"])
@requires_role(Roles.EMPLOYEE)
def save_session():
    request.form.items()

    sessions = list(request.form.items())

    # Save provisionally booked sessions.
    session["booked_sessions"] += [
        sess[1] for sess in sessions if sess[1] not in session["booked_sessions"]
    ]
    session.modified = True
    flash("Added to basket", "success")

    return redirect(url_for("employee.booking"))


@employee.route("/checkout")
@requires_role(Roles.EMPLOYEE)
def basket():
    sess_objs = []
    valid = True
    for sess in session["booked_sessions"]:
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
        user = User.get_by_id(session["customer_id"])
        s.users.append(user)
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


@employee.route("/manage_sessions")
@requires_role(Roles.EMPLOYEE)
def manage_sessions():
    user = User.get_by_id(session["customer_id"])

    sessions = user.sessions

    sessions = [
        (sess, True) if session_expired(sess) else (sess, False) for sess in sessions
    ]

    return render_template("session_management.html", sessions=sessions)


@employee.route("/delete_session/<id>", methods=["GET", "POST"])
@requires_role(Roles.EMPLOYEE)
def delete_session(id):
    user = User.get_by_id(session["customer_id"])
    target_session = db.session.execute(
        select(Session).where(Session.session_id == id)
    ).scalar()

    target_session.users.remove(user)

    # if a session has no attendees then remove it from the db.
    if len(target_session.users) == 0:
        db.session.delete(target_session)

    db.session.commit()
    return redirect(url_for("employee.manage_sessions"))


@employee.route("/settings", methods=["POST", "GET"])
@requires_role(Roles.EMPLOYEE)
def settings():
    user = User.get_by_id(session["customer_id"])

    form = UpdateUserDetailsForm(data={"email": user.email, "username": user.username})
    del form.current_password
    del form.new_password
    del form.confirm

    if form.validate_on_submit():
        # Update username if it has changed and is not taken
        if form.username.data != user.username:
            if update_username(form.username.data, user) is None:
                flash("Could not use that username", "warning")
                return redirect(url_for("employee.settings"))
            session["customer_name"] = form.username.data

        # Update email if it has changed and is valid + not taken
        if form.email.data != user.email:
            if update_email(form.email.data, user) is None:
                flash("Could not use that email", "warning")
                return redirect(url_for("employee.settings"))

        flash("Updated account", "success")

    return render_template("settings.html", form=form)


@employee.route("/settings/delete_account", methods=["POST", "GET"])
@requires_role(Roles.EMPLOYEE)
def delete_account():
    user = User.get_by_id(session["customer_id"])
    if user.stripe_id is not None:
        try:
            stripe.Customer.delete(user.stripe_id)
        except stripe.error.InvalidRequestError as e:
            print(str(e))

    db.session.delete(user)
    db.session.commit()
    flash("Account Deleted", "success")

    return redirect(url_for("main.index"))


@employee.route("/settings/payment_info")
@requires_role(Roles.EMPLOYEE)
def payment_info():
    user = User.get_by_id(session["customer_id"])
    customer = None
    if user.stripe_id is None:
        customer = stripe.Customer.create(email=user.email)
    if customer:
        user.stripe_id = customer.id
        db.session.commit()

    portal = None
    try:
        portal = stripe.billing_portal.Session.create(
            customer=user.stripe_id,
            return_url=url_for("employee.settings", _external=True),
        )
    except stripe.error.InvalidRequestError:
        flash("Could not create billing portal", "warning")

    if portal is not None:
        return redirect(portal.url)

    return redirect(url_for("employee.settings"))


@employee.route("/end_session")
@requires_role(Roles.EMPLOYEE)
def end_session():
    session.pop("customer_id")
    session.pop("customer_name")
    session.pop("booked_sessions")

    return redirect(url_for("employee.index"))
