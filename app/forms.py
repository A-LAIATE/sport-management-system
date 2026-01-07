from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, EqualTo, Optional
import wtforms.fields
from app.models import Days, Facilities, Activities, Roles


class SignUpForm(FlaskForm):
    email = wtforms.fields.EmailField("Email", validators=[DataRequired()])
    username = wtforms.fields.StringField("Username", validators=[DataRequired()])
    password = wtforms.fields.PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=64)]
    )
    confirm = wtforms.fields.PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            Length(min=8, max=64),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = wtforms.fields.SubmitField("Sign Up")


class LoginForm(FlaskForm):
    identifier = wtforms.fields.StringField(
        "Username or Email", validators=[DataRequired()]
    )
    password = wtforms.fields.PasswordField(
        "Password", validators=[DataRequired(), Length(max=64)]
    )
    submit = wtforms.fields.SubmitField("Log In")


class ActivitySelectForm(FlaskForm):
    type = wtforms.fields.RadioField(
        "Activity Type",
        choices=[
            ("general", "General Use"),
            ("team", "Team Use"),
            ("class", "Classes"),
        ],
    )
    date = wtforms.fields.DateField("Date")

    submit = wtforms.fields.SubmitField("Find Sessions")


class UserSearchForm(FlaskForm):
    identifier = wtforms.fields.StringField(
        "Customers username or email:", validators=[DataRequired()]
    )
    search = wtforms.fields.SubmitField("Search")


class UpdateUserDetailsForm(FlaskForm):
    email = wtforms.fields.EmailField("Email", validators=[DataRequired()])
    username = wtforms.fields.StringField("Username", validators=[DataRequired()])
    current_password = wtforms.fields.PasswordField(
        "Current Password", validators=[DataRequired(), Length(min=8, max=64)]
    )
    new_password = wtforms.fields.PasswordField(
        "New Password", validators=[Length(min=8, max=64), Optional()]
    )
    confirm = wtforms.fields.PasswordField(
        "Confirm new Password",
        validators=[
            Optional(),
            Length(min=8, max=64),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )
    submit = wtforms.fields.SubmitField(
        "Update", render_kw={"class": "btn btn-primary"}
    )


class ReAuthForm(FlaskForm):
    password = wtforms.fields.PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=64)]
    )
    submit = wtforms.fields.SubmitField(
        "Authenticate", render_kw={"class": "btn btn-primary"}
    )
    date = wtforms.fields.DateField("Date")
    submit = wtforms.fields.SubmitField("Find Sessions")


class EditActivityForm(FlaskForm):
    activity_id = wtforms.fields.IntegerField()
    activity_type = wtforms.fields.SelectField(
        choices=[(e.value, e.name) for e in Activities]
    )
    facility_id = wtforms.fields.SelectField(
        choices=[(e.value, e.name) for e in Facilities]
    )
    day = wtforms.fields.SelectField(choices=[(e.value, e.name) for e in Days])
    start_time = wtforms.fields.TimeField()
    end_time = wtforms.fields.TimeField()

    edit = wtforms.fields.SubmitField("Save", render_kw={"class": "btn btn-primary"})


class EditUserForm(FlaskForm):
    editing_user_id = wtforms.fields.HiddenField("editing_user_id")
    username = wtforms.fields.StringField()
    email = wtforms.fields.StringField()
    stripe_id = wtforms.fields.StringField()

    edit = wtforms.fields.SubmitField("Edit", render_kw={"class": "btn btn-primary"})


class EditFacilityForm(FlaskForm):
    max_capacity = wtforms.fields.IntegerField()
    start_time = wtforms.fields.TimeField()
    end_time = wtforms.fields.TimeField()

    edit = wtforms.fields.SubmitField("Edit", render_kw={"class": "btn btn-primary"})


class EditEmployeeForm(FlaskForm):
    editing_user_id = wtforms.fields.HiddenField("editing_user_id")
    username = wtforms.fields.StringField()
    role = wtforms.fields.SelectField(
        choices=[
            (Roles.EMPLOYEE.value, Roles.EMPLOYEE.name),
            (Roles.ADMIN.value, Roles.ADMIN.name),
        ]
    )

    edit = wtforms.fields.SubmitField("Edit", render_kw={"class": "btn btn-primary"})


class AddEmployeeForm(FlaskForm):
    editing_user_id = wtforms.fields.HiddenField("editing_user_id")
    username = wtforms.fields.StringField("Username", validators=[DataRequired()])
    password = wtforms.fields.PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=64)]
    )
    confirm = wtforms.fields.PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            Length(min=8, max=64),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    role = wtforms.fields.SelectField(
        choices=[
            (Roles.EMPLOYEE.value, Roles.EMPLOYEE.name),
            (Roles.ADMIN.value, Roles.ADMIN.name),
        ]
    )

    edit = wtforms.fields.SubmitField(
        "Create Employee", render_kw={"class": "btn btn-primary"}
    )


class PricingForm(FlaskForm):
    price_per_session = wtforms.fields.DecimalField(
        "The price of a 1-hour session in £",
        places=2,
        validators=[DataRequired()],
        render_kw={"class": ".form-control-plaintext", "readonly": True},
    )

    discount_threshhold = wtforms.fields.IntegerField(
        "Minumum number of sessions to qualify for Bulk discount:",
        validators=[DataRequired()],
        render_kw={"class": ".form-control-plaintext", "readonly": True},
    )
    discount_percent_off = wtforms.fields.DecimalField(
        "% Discount applied by Bulk discount:",
        validators=[DataRequired()],
        render_kw={"class": ".form-control-plaintext", "readonly": True},
    )

    # update = wtforms.fields.SubmitField("Update")
