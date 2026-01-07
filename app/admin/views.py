from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.utils import (
    requires_role,
    get_user_by_username,
    get_user_by_email,
    create_user,
    get_delta_hours,
)
from flask_login import current_user
from app.models import (
    Roles,
    Activity,
    User,
    Facility,
    Activities,
    Facilities,
    Days,
)
from app import db, hasher, stripe
from sqlalchemy import select
import sqlalchemy
from app.forms import (
    EditActivityForm,
    EditUserForm,
    EditFacilityForm,
    EditEmployeeForm,
    AddEmployeeForm,
    PricingForm,
)

admin = Blueprint(
    "admin",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/admin",
)


@admin.route("/")
@requires_role(Roles.ADMIN)
def index():
    return render_template("m_dashboard.html")


@admin.route("/activities")
@requires_role(Roles.ADMIN)
def activities():
    activity_list = db.session.execute(select(Activity)).all()
    # .all() gives results in a list of (object,) tuples
    activity_list = [act[0].admin_data() for act in activity_list]

    if len(activity_list) == 0:
        return render_template(
            "show_db_data.html",
            title="Activities",
            edit_action="admin.edit_activity",
        )

    return render_template(
        "show_db_data.html",
        title="Activities",
        columns=activity_list[0].keys(),
        data=activity_list,
        edit_action="admin.edit_activity",
        delete_from="activity",
        message="Deleting an Activity does not effect already booked sessions.",
    )


@admin.route("/activities/edit", methods=["POST"])
@admin.route("/activities/edit/<id>", methods=["GET", "POST"])
@requires_role(Roles.ADMIN)
def edit_activity(id=None):
    activity = db.session.execute(
        select(Activity).where(Activity.activity_id == id)
    ).scalar()

    form = EditActivityForm()

    if form.validate_on_submit():
        # Find the difference in hours between the start and end time
        delta = get_delta_hours(form.start_time.data, form.end_time.data)

        # Session must be at least 1 hour long
        if delta < 1:
            flash("Duration too short. Must be 1 hour minimum", "warning")
            return render_template("edit_activity.html", form=form)

        activity = set_activity_from_form(activity, form)
        db.session.commit()

        flash("Updated (not really)", "success")
        return redirect(url_for("admin.activities"))

        # Cannot be overlapping with existing activity of same type in facility
        # e.g. if LANESWIM in POOL 8am to 8pm exists then:
        # LANESWIM in POOL 12pm to 5pm should be rejected (any with start_time before 8pm should be, in fact)
        # GENERAL in POOL 12pm to 5pm should be accepted (assuming there are no other GENERAL POOL activities that day)
        # activity_id should be unique

    form = set_form_from_activity(form, activity)

    return render_template(
        "edit_page.html",
        title="Edit Activity",
        form=form,
        action=url_for("admin.edit_activity", id=id),
    )


@admin.route("/members")
@requires_role(Roles.ADMIN)
def members():
    members = db.session.execute(select(User).where(User.role == Roles.CUSTOMER)).all()
    members = [member[0].admin_data() for member in members]

    if len(members) == 0:
        return render_template(
            "show_db_data.html",
            title="Members",
            edit_action="admin.edit_activity",
        )

    return render_template(
        "show_db_data.html",
        title="Members",
        columns=members[0].keys(),
        data=members,
        edit_action="admin.edit_member",
        delete_from="user",
    )


@admin.route("/members/edit/", methods=["POST"])
@admin.route("/members/edit/<id>", methods=["POST", "GET"])
@requires_role(Roles.ADMIN)
def edit_member(id=None):
    member = db.session.execute(select(User).where(User.user_id == id)).scalar()
    form = EditUserForm(obj=member)

    # Hidden field that stores the id of the member being edited
    form.editing_user_id.data = member.user_id

    if form.validate_on_submit():
        # If username has been changed, check that it is unique
        if (
            get_user_by_username(form.username.data) is not None
            and form.username.data != member.username
        ):
            flash("Username taken", "warning")
            return redirect(url_for("admin.edit_member", user_id=id))

        # If email has been changed, check that it is unique
        if (
            get_user_by_email(form.email.data) is None
            and form.email.data != member.email
        ):
            flash("Email taken", "warning")
            return redirect(url_for("admin.edit_member", user_id=id))

        # TODO check if stripe_id is invalid.

        member.email = form.email.data
        member.username = form.username.data

        db.session.commit()

        flash("Updated", "success")
        return redirect(url_for("admin.members"))

    return render_template(
        "edit_page.html",
        title=member.username,
        form=form,
        action=url_for("admin.edit_member", id=id),
        danger_message="Note that  username, email must be unique. Only change the stripe_id if you know what you are doing",
    )


@admin.route("/facilities")
@requires_role(Roles.ADMIN)
def facilities():
    facils = db.session.execute(select(Facility)).all()
    facil_data = [facil[0].admin_data() for facil in facils]

    if len(facil_data) == 0:
        return render_template(
            "show_db_data.html",
            title="Activities",
            edit_action="admin.edit_activity",
        )

    return render_template(
        "show_db_data.html",
        title="Facilities",
        columns=facil_data[0].keys(),
        data=facil_data,
        edit_action="admin.edit_facility",
        delete_from="facility",
        message="Modifying or Deleting a Facility does not effect already booked sessions.",
    )


@admin.route("/facilities/edit", methods=["POST"])
@admin.route("/facilities/edit/<id>", methods=["POST", "GET"])
@requires_role(Roles.ADMIN)
def edit_facility(id=None):
    facility = db.session.execute(select(Facility).where(Facility.id == id)).scalar()

    form = EditFacilityForm(obj=facility)
    check_details = False

    if form.validate_on_submit():
        # Find the difference in hours between the start and end time
        delta = get_delta_hours(form.start_time.data, form.end_time.data)

        # Session must be at least 1 hour long
        if delta < 1:
            flash("Invalid opening and closing time.", "danger")
            return redirect(url_for("admin.edit_facility", id=id))

        if delta < 8:
            flash(
                f"The facility is open for {delta} hours. Is this correct?",
                "warning",
            )
            check_details = True

        if form.max_capacity.data <= 0:
            flash("Capacity set to 0 or less. Was this a mistake?", "warning")
            check_details = True

        form.populate_obj(facility)

        db.session.commit()
        flash("Updated", "success")
        if check_details:
            return redirect(url_for("admin.edit_facility", id=id))

        return redirect(url_for("admin.facilities"))

    return render_template(
        "edit_page.html",
        title=facility.facility_id,
        form=form,
        action=url_for("admin.edit_facility", id=id),
    )


@admin.route("/employees")
@requires_role(Roles.ADMIN)
def employees():
    employees = db.session.execute(
        select(User).where((User.role == Roles.ADMIN) | (User.role == Roles.EMPLOYEE))
    )
    employees = [em[0].admin_data() for em in employees]

    if len(employees) == 0:
        return render_template(
            "show_db_data.html",
            title="Employees",
            edit_action="admin.edit_activity",
        )

    return render_template(
        "show_db_data.html",
        title="Employees",
        columns=employees[0].keys(),
        data=employees,
        edit_action="admin.edit_employee",
        add_action="admin.add_employee",
        delete_from="user",
    )


@admin.route("/employees/edit", methods=["POST"])
@admin.route("/employees/edit/<id>", methods=["POST", "GET"])
@requires_role(Roles.ADMIN)
def edit_employee(id=None):
    employee = db.session.execute(select(User).where(User.user_id == id)).scalar()
    form = EditEmployeeForm()
    form.editing_user_id = employee.user_id

    if form.validate_on_submit():
        existing = get_user_by_username(form.username.data)
        if existing is not None:
            flash("Username already in use", "warning")
            return redirect(url_for("admin.edit_employee", id=id))

        employee.username = form.username.data
        employee.role = Roles(int(form.role.data))
        db.session.commit()

        flash("Updated", "success")
        return redirect(url_for("admin.employees"))

    # Can't set default role by passing employee so do it manually
    form.role.default = employee.role.value
    form.username.default = employee.username
    form.process()

    return render_template(
        "edit_page.html",
        title=employee.username,
        form=form,
        action=url_for("admin.edit_employee", id=id),
    )


@admin.route("/employees/add", methods=["POST", "GET"])
@requires_role(Roles.ADMIN)
def add_employee():
    form = AddEmployeeForm()

    if form.validate_on_submit():
        role = Roles(int(form.role.data))
        employee = create_user(
            "", form.username.data, hasher.hash(form.password.data), role
        )
        if employee is not None:
            flash("Created new Employee", "success")
            return redirect(url_for("admin.employees"))

        flash("Could not create employee", "warning")

    return render_template(
        "edit_page.html",
        title="Create Employee",
        form=form,
        action=(url_for("admin.add_employee")),
    )


@admin.route("/delete/<table>/<id>", methods=["POST", "GET"])
@requires_role(Roles.ADMIN)
def delete(table, id):
    obj_to_delete = None
    if table == "user":
        obj_to_delete = db.session.execute(
            select(User).where(User.user_id == id)
        ).scalar()

        if obj_to_delete.user_id == current_user.user_id:
            flash("Don't delete the account you are logged in from.", "warning")
            return redirect(request.referrer)

    if table == "facility":
        obj_to_delete = db.session.execute(
            select(Facility).where(Facility.id == id)
        ).scalar()

        # Delete all associated activities.
        db.session.execute(
            sqlalchemy.delete(Activity).where(
                Activity.facility_id == obj_to_delete.facility_id
            )
        )

    if table == "activity":
        obj_to_delete = db.session.execute(
            select(Activity).where(Activity.activity_id == id)
        ).scalar()

    db.session.delete(obj_to_delete)
    db.session.commit()

    flash(f"removed {obj_to_delete}", "danger")

    return redirect(request.referrer)


@admin.route("/pricing", methods=["POST", "GET"])
@requires_role(Roles.ADMIN)
def pricing():
    # Get session price object
    session_price_obj = stripe.Price.retrieve("price_1MjVTtDYqRgnWN5816Uv17Ee")

    # Price in pence per session
    pence_per_session = session_price_obj.unit_amount

    # Get discount object
    discount = stripe.Coupon.retrieve("GME4R3Fv")

    form = PricingForm(
        data={
            "price_per_session": pence_per_session / 100,
            "discount_percent_off": discount.percent_off,
            "discount_threshhold": discount.metadata["quantity_threshold"],
        }
    )
    return render_template(
        "edit_pricing.html",
        form=form,
        danger_message="Pricing can be changed from the Stripe Dashboard",
    )

    # Get discount threshold.


def set_form_from_activity(form, activity):
    form.activity_id.default = activity.activity_id
    form.activity_type.default = activity.activity_type.value
    form.facility_id.default = activity.facility_id.value
    form.day.default = activity.day.value
    form.start_time.default = activity.start_time
    form.end_time.default = activity.end_time
    form.process()
    return form


def set_activity_from_form(activity, form):
    activity.activity_id = form.activity_id.data
    activity.activity_type = Activities(int(form.activity_type.data))
    activity.facility_id = Facilities(int(form.facility_id.data))
    activity.day = Days(int(form.day.data))
    activity.start_time = form.start_time.data
    activity.end_time = form.end_time.data

    return activity
