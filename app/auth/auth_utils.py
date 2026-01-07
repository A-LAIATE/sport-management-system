from flask import session, Response, url_for, redirect, flash
from flask_login import current_user
from app.models import Roles, Session, Membership, User
import datetime
from app import stripe, db
import stripe.error


def determine_login_destination() -> Response:
    """
    Returns a destination based on the request to /login.
    Will return the url_for the next= param if it is valid, then falls back to the index pages for each role.

    Raises a TypeError if the page for role is not defined in the function
    """
    dest = ""
    try:
        dest = session["next"]
    except KeyError:
        return user_home()

    if dest:
        # Avoid any issues with using out of date `next` urls.
        session["next"] = None
        return redirect(dest)

    return user_home()


def user_home() -> Response:
    """
    Returns a redirect to correct home page for each user role.
    """
    if current_user.role is Roles.CUSTOMER:
        return redirect(url_for("customer.index"))

    if current_user.role is Roles.ADMIN:
        return redirect(url_for("admin.index"))
    if current_user.role is Roles.EMPLOYEE:
        return redirect(url_for("employee.index"))

    raise TypeError(f" user role {current_user.role} unknown ")


def can_apply_bulk_discount(dates: "list[datetime.datetime]") -> bool:
    """
    Given all the datetimes of the sessions in user's basket,
     if there are 3 or more sessions within 7 days of each other then return True.
    """
    if len(dates) >= 3:
        for date in dates:
            count = 0
            for comp_date in dates:
                delta = date - comp_date
                if abs(delta.days) <= 7:
                    count += 1
                if count >= 3:
                    return True
    return False


def get_stripe_customer_from_user(user):
    stripe_id = user.stripe_id
    if stripe_id is None:
        customer = stripe.Customer.create(
            email=user.email,
        )
        user.stripe_id = customer.id
        db.session.commit()
    else:
        customer = stripe.Customer.retrieve(user.stripe_id)

    return customer


def create_booking_checkout(user: "User" = current_user):
    customer = get_stripe_customer_from_user(user)
    if user.membership != Membership.NONE:
        return redirect(url_for("auth.booking_success"))

    discounts = []
    dates = [
        Session.from_unique_code(code=s).start_time for s in session["booked_sessions"]
    ]

    if can_apply_bulk_discount(dates):
        # Apply 15% discount for booking 3+ within 7 days of each other
        discounts = [{"coupon": "GME4R3Fv"}]
    else:
        discounts = []

    metadata = {}
    if current_user.role == Roles.EMPLOYEE:
        print("added metadata")
        metadata = {"employee_id": current_user.user_id}

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            line_items=[
                {
                    "price": "price_1MjVTtDYqRgnWN5816Uv17Ee",
                    "quantity": len(session["booked_sessions"]),
                },
            ],
            discounts=discounts,
            mode="payment",
            payment_intent_data={"setup_future_usage": "on_session"},
            success_url=url_for("auth.booking_success", _external=True),
            cancel_url=url_for("auth.transaction_cancelled", _external=True),
            submit_type="book",
            metadata=metadata,
            invoice_creation={"enabled": True},
        )
    except stripe.error.InvalidRequestError as e:
        if "email" in str(e):
            flash(
                "Your email is incompatible with stripe, please update it in the settings page",
                "danger",
            )
            return redirect("customer.settings")
        return str(e)

    return redirect(checkout_session.url, code=303)
