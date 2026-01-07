from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    jsonify,
)
from flask_login import login_user, current_user, logout_user
from app import hasher, db, stripe
from app.forms import SignUpForm, LoginForm, ReAuthForm
from app.utils import (
    create_user,
    verify_credentials,
    requires_role,
    get_user_by_stripe_id,
    get_user_by_email,
)
from .auth_utils import user_home, determine_login_destination, create_booking_checkout
from app.models import Roles, Session, Membership, User
import json
from sqlalchemy import select
import datetime
from argon2.exceptions import VerifyMismatchError


auth = Blueprint(
    "auth",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/auth",
)


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:  # User already logged in
        flash("You are already Logged In", "info")
        return user_home()

    form = SignUpForm()

    if form.validate_on_submit():
        # Not a good way to test emails, but https://www.netmeister.org/blog/email.html (TLDR: its hard to do properly)
        # Plus the form *should* catch most issues.
        if "@" not in form.email.data:
            flash("Invalid email.", "danger")
            return redirect(url_for("auth.signup"))

        user = create_user(
            form.email.data,
            form.username.data.lower(),
            hasher.hash(form.password.data),
        )

        if user is None:  # Username taken
            flash("Signup failed.", "danger")
            return redirect(url_for("auth.signup"))

        login_user(user)
        flash("Welcome to the site", "info")

        return user_home()

    return render_template("signup.html", form=form)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:  # User already logged in
        flash("You are already Logged In", "info")
        return user_home()

    form = LoginForm()

    if request.args.get("next"):
        # The post request for submitting the form clears this so save it.
        session["next"] = request.args.get("next")

    if form.validate_on_submit():
        user = verify_credentials(form.identifier.data, form.password.data)

        if not user:
            flash("Error: Invalid Credentials", "danger")
            return redirect(url_for("auth.login"))

        login_user(user)
        return determine_login_destination()

    return render_template("login.html", form=form)


@auth.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Logged Out", "info")
    return redirect(url_for("main.index"))


@auth.route("/monthly_membership_checkout_session")
@requires_role(Roles.CUSTOMER)
def monthly_membership_checkout():
    customer = None
    if current_user.stripe_id is None:
        customer = stripe.Customer.create(
            email=current_user.email, name=current_user.username
        )
    if customer:
        current_user.stripe_id = customer.id
        db.session.commit()

    # Don't let users purchase a memberhsip if they alread have one
    if current_user.membership != Membership.NONE:
        flash("You already have a membership", "info")
        return redirect(url_for("customer.settings"))

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price": "price_1MmK85DYqRgnWN58F8HlKPtV",
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=url_for("auth.membership_success", _external=True),
            cancel_url=url_for("auth.transaction_cancelled", _external=True),
            customer=current_user.stripe_id,
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


@auth.route("/annual_membership_checkout_session")
@requires_role(Roles.CUSTOMER)
def annual_membership_checkout():
    customer = None
    if current_user.stripe_id is None:
        customer = stripe.Customer.create(email=current_user.email)
    if customer:
        current_user.stripe_id = customer.id
        db.session.commit()

    # Don't let users purchase a memberhsip if they alread have one
    if current_user.membership != Membership.NONE:
        flash("You already have a membership", "info")
        return redirect(url_for("customer.settings"))

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price": "price_1MmK8aDYqRgnWN58BDC0xJzE",
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=url_for("auth.membership_success", _external=True),
            cancel_url=url_for("auth.transaction_cancelled", _external=True),
            customer=current_user.stripe_id,
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


@auth.route("/membership_success")
def membership_success():
    flash("Enjoy your new membership", "success")
    return user_home()


@auth.route("/cancel")
def transaction_cancelled():
    flash("Transaction Cancelled", "danger")
    return user_home()


@auth.route("/webhook", methods=["POST"])
def webhook():
    endpoint_secret = (
        "whsec_70343dd36acef1164294ddd00d6a1086cc2173c3bf216ec5db495e6e29214953"
    )
    event = None
    payload = request.data

    try:
        event = json.loads(payload)
    except Exception as e:
        print("Error" + str(e))
        return jsonify(success=False)

    if endpoint_secret:
        # Only verify the event if there is an endpoint secret defined
        # Otherwise use the basic event deserialized with json
        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except stripe.error.SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed." + str(e))
            return jsonify(success=False)

    # Handle the event
    if event:
        if event.type == "payment_intent.succeeded":
            handle_payment_success(event)
        elif event.type == "customer.subscription.updated":
            handle_subscription_change(event)
        elif event.type == "customer.created":
            handle_new_customer(event)

    return jsonify(success=True)


def handle_payment_success(event):
    # print(event.data.object)
    pass


def handle_new_customer(event):
    object = event.data.object

    email = object["email"]
    user = get_user_by_email(email)
    user.stripe_id = object["id"]
    db.session.commit()


def handle_subscription_change(event):
    object = event["data"]["object"]
    customer = object["customer"]
    user = get_user_by_stripe_id(customer)
    if user is None:
        print("GOT INVALID customer_id from stripe")
        return

    # If payment failed
    if object["status"] != "active":
        user.membership = Membership.NONE
        user.membership_expiration_date = None

    else:
        subscription_type = object["plan"]["interval"]
        if subscription_type == "year":
            user.membership = Membership.YEAR
        elif subscription_type == "month":
            user.membership = Membership.MONTH
        else:
            print("UNKNOWN SUBSCRIPTION TYPE IN RESPONSE")

        expires = object["current_period_end"]
        user.membership_expiration_date = datetime.datetime.fromtimestamp(expires)

    db.session.commit()


@auth.route("/booking-checkout-session", methods=["POST"])
def booking_checkout_session():
    if current_user.role == Roles.EMPLOYEE:
        checkout = create_booking_checkout(User.get_by_id(session["customer_id"]))
    else:
        checkout = create_booking_checkout(current_user)
    return checkout


@auth.route("/booking/success")
def booking_success():
    if current_user.role == Roles.EMPLOYEE:
        user = User.get_by_id(session["customer_id"])
    else:
        user = current_user

    if session["booked_sessions"]:
        sess_objs = []
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
            s.users.append(user)
            sess_objs.append(s)
            db.session.add(s)
        db.session.commit()
        session["booked_sessions"] = []
        flash("Booked", "success")
    return user_home()


@auth.route("/cancel")
def cancel():
    return "Cancelled"


@auth.route("/reauth", methods=["POST", "GET"])
@requires_role(Roles.CUSTOMER)
def reauth():
    form = ReAuthForm()
    if request.args.get("next"):
        # The post request for submitting the form clears this so save it.
        session["next"] = request.args.get("next")

    if form.validate_on_submit():
        try:
            hasher.verify(current_user.password, form.password.data)
        except VerifyMismatchError:
            flash("Incorrect Password", "danger")
            return redirect(request.referrer)

        return redirect(session.pop("next"))

    return render_template("reauth.html", form=form)
