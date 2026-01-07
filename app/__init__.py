from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import select
from argon2 import PasswordHasher
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET")
# We init the db object
db = SQLAlchemy()
login_manager = LoginManager()
# Use argon2-id for password hashing
hasher = PasswordHasher()


def create_app(testing=False):
    app = Flask(__name__, template_folder="./templates")

    # This loads the flask configuration data from config.py
    try:
        app.config.from_pyfile("config.py")
    except ValueError as e:
        if testing:
            app.config["SECRET_KEY"] = "testing"
        else:
            raise e

    # Tell flask where the db is.

    if app.config["DEBUG"]:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///leisure_centre.db"

    elif testing:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///leisure_centre_test.db"

    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///PROD_leisure_centre.db"

    db.init_app(app)

    login_manager.init_app(app)

    # This is required by flask_login
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.execute(
            select(User).where(User.user_id == int(user_id))
        ).scalar()

    @app.before_request
    def init_session_vars():
        if not session.get("booked_sessions"):
            session["booked_sessions"] = []
        if not session.get("next"):
            session["next"] = ""

    @app.context_processor
    def make_Roles_available():
        from app.models import Roles

        return dict(Roles=Roles)

    # import and register the view blueprints here. This lets our app acually use them.
    from .main_views import main
    from app.auth.views import auth
    from app.customer.views import customer
    from app.admin.views import admin
    from app.employee.views import employee

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(customer)
    app.register_blueprint(admin)
    app.register_blueprint(employee)

    return app


# Add some users to the db for debugging.
def debugging_add_to_db(db):
    from .models import Roles, Membership
    from app.utils import create_user
    import warnings
    import datetime

    cust = create_user("cust@mail.com", "cust", hasher.hash("password"))
    cust2 = create_user("cust2@mail.com", "cust2", hasher.hash("password"))
    admin = create_user("admin@mail.com", "admin", hasher.hash("password"), Roles.ADMIN)
    cust.stripe_id = "cus_NcETZzMmfSmWYd"
    cust.membership = Membership.YEAR
    cust.membership_expiration_date = datetime.datetime.now() + datetime.timedelta(
        days=5
    )
    employee = create_user("", "employee", hasher.hash("password"), Roles.EMPLOYEE)

    warnings.warn("WARNING: DB CONTAINS INSECURE CREDENTIALS")

    db.session.add(cust)
    db.session.add(cust2)
    db.session.add(admin)
    db.session.add(employee)
    db.session.commit()


def init_db(db):
    from app.utils import create_user
    from .models import Roles

    create_user("admin@admin.com", "admin", hasher.hash("adminpassword"), Roles.ADMIN)
    add_facilities(db)
    add_activities(db)


def debugging_add_sessions_to_cust(db):
    from .models import Facilities, Activities, Session, User
    import datetime
    import warnings

    s1 = Session(
        session_type=Activities.SWIMLESSON,
        facility_id=Facilities.POOL,
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(hours=1),
        is_class=0,
    )

    s2 = Session(
        session_type=Activities.SWIMLESSON,
        facility_id=Facilities.CLIMBING,
        start_time=datetime.datetime.now() + datetime.timedelta(hours=1),
        end_time=datetime.datetime.now() + datetime.timedelta(hours=2),
        is_class=0,
    )

    s3 = Session(
        session_type=Activities.SWIMLESSON,
        facility_id=Facilities.SQUASH,
        start_time=datetime.datetime.now() + datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(days=1, hours=1),
        is_class=0,
    )

    s4 = Session(
        session_type=Activities.SWIMLESSON,
        facility_id=Facilities.STUDIO,
        start_time=datetime.datetime.now() + datetime.timedelta(days=3),
        end_time=datetime.datetime.now() + datetime.timedelta(days=3, hours=1),
        is_class=0,
    )

    s5 = Session(
        session_type=Activities.SWIMLESSON,
        facility_id=Facilities.HALL,
        start_time=datetime.datetime.now() - datetime.timedelta(days=1),
        end_time=datetime.datetime.now() + datetime.timedelta(hours=1, days=-1),
        is_class=0,
    )
    warnings.warn("WARNING: DB CONTAINS FAKE SESSIONS")

    user = db.session.execute(select(User).where(User.username == "cust")).scalar()

    user.sessions.append(s1)
    user.sessions.append(s2)
    user.sessions.append(s3)
    user.sessions.append(s4)
    user.sessions.append(s5)
    db.session.commit()


def add_facilities(db):
    """
    Add each facility to the db with details as defined in spec doument.
    """
    from .models import Facilities, Facility
    import datetime

    pool = Facility(
        facility_id=Facilities.POOL,
        start_time=datetime.time(8),
        end_time=datetime.time(20),
        max_capacity=30,
    )
    fitness = Facility(
        facility_id=Facilities.FITNESS,
        start_time=datetime.time(8),
        end_time=datetime.time(22),
        max_capacity=35,
    )
    squash = Facility(
        facility_id=Facilities.SQUASH,
        start_time=datetime.time(8),
        end_time=datetime.time(22),
        max_capacity=8,
    )
    sports = Facility(
        facility_id=Facilities.HALL,
        start_time=datetime.time(8),
        end_time=datetime.time(22),
        max_capacity=45,
    )
    climbing = Facility(
        facility_id=Facilities.CLIMBING,
        start_time=datetime.time(10),
        end_time=datetime.time(22),
        max_capacity=22,
    )
    studio = Facility(
        facility_id=Facilities.STUDIO,
        start_time=datetime.time(8),
        end_time=datetime.time(22),
        max_capacity=25,
    )
    db.session.add(pool)
    db.session.add(fitness)
    db.session.add(squash)
    db.session.add(sports)
    db.session.add(climbing)
    db.session.add(studio)
    db.session.commit()


def add_activities(db):
    """
    Add each activity to the db.
    """
    from .models import Activities, Activity, Facilities, Days
    import datetime

    # Each of these follow the format of (start hour, end hour, [list of activites availble during that timeframe])
    # One row for each day, for each facility.
    pool_times = [
        [(8, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON])],
        [(8, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON])],
        [(8, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON])],
        [(8, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON])],
        [
            (8, 10, [Activities.TEAM]),
            (10, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON]),
        ],
        [(8, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON])],
        [
            (8, 10, [Activities.TEAM]),
            (10, 20, [Activities.GENERAL, Activities.LANESWIM, Activities.SWIMLESSON]),
        ],
    ]

    fitness_times = [
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
    ]

    squash_times = [
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
    ]

    sports_times = [
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [(8, 22, [Activities.GENERAL])],
        [
            (8, 19, [Activities.GENERAL]),
            (19, 21, [Activities.TEAM]),
            (21, 22, [Activities.GENERAL]),
        ],
        [(8, 22, [Activities.GENERAL])],
        [
            (8, 9, [Activities.GENERAL]),
            (9, 11, [Activities.TEAM]),
            (11, 22, [Activities.GENERAL]),
        ],
        [(8, 22, [Activities.GENERAL])],
    ]

    climb_times = [
        [(10, 20, [Activities.GENERAL])],
        [(10, 20, [Activities.GENERAL])],
        [(10, 20, [Activities.GENERAL])],
        [(10, 20, [Activities.GENERAL])],
        [(10, 20, [Activities.GENERAL])],
        [(10, 20, [Activities.GENERAL])],
        [(10, 20, [Activities.GENERAL])],
    ]
    studio_times = [
        [(18, 19, [Activities.PILATES])],
        [(10, 11, [Activities.AEROBICS])],
        [(-1, -1, [])],
        [(19, 20, [Activities.AEROBICS])],
        [(19, 20, [Activities.YOGA])],
        [(10, 11, [Activities.AEROBICS])],
        [(9, 10, [Activities.YOGA])],
    ]

    for facil_id, timetable in enumerate(
        [
            pool_times,
            fitness_times,
            squash_times,
            sports_times,
            climb_times,
            studio_times,
        ]
    ):
        for day, details in enumerate(timetable):
            for open, close, uses in details:
                if open == -1:
                    continue
                for use in uses:
                    a = Activity(
                        activity_type=use,
                        facility_id=Facilities(facil_id),
                        day=Days(day),
                        start_time=datetime.time(open),
                        end_time=datetime.time(close),
                    )
                    db.session.add(a)
    db.session.commit()
