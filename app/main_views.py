from flask import Blueprint, render_template
from .auth.auth_utils import user_home
from flask_login import current_user

main = Blueprint("main", __name__, static_folder="static", template_folder="templates")


@main.route("/")
def index():
    if not current_user.is_authenticated:
        return render_template("index.html")

    return user_home()


@main.route("/facilities")
def facilities():
    return render_template("facilities.html")


@main.route("/pricing")
def pricing():
    return render_template("pricing.html")
