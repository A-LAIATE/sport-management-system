from . import db
from flask_login import UserMixin
from sqlalchemy import Enum, select
import sqlalchemy as sqla
import json
import enum
import datetime


class Roles(enum.Enum):
    CUSTOMER = 1
    EMPLOYEE = 2
    ADMIN = 3


class Days(enum.Enum):
    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6


class Facilities(enum.Enum):
    POOL = 0
    FITNESS = 1
    SQUASH = 2
    HALL = 3
    CLIMBING = 4
    STUDIO = 5


class Activities(enum.Enum):
    GENERAL = 0
    LANESWIM = 1
    SWIMLESSON = 2
    TEAM = 3
    PILATES = 4
    YOGA = 5
    AEROBICS = 6


class Membership(enum.Enum):
    NONE = 0
    MONTH = 1
    YEAR = 2


# Convert the ENUM to human-friendly text
act_to_str = {
    Activities.GENERAL: "General Use",
    Activities.LANESWIM: "Lane Swim",
    Activities.SWIMLESSON: "Swimming Lesson",
    Activities.TEAM: "Team Activity",
    Activities.PILATES: "Pilates Class",
    Activities.YOGA: "Yoga Class",
    Activities.AEROBICS: "Aerobics Class",
}

facil_to_str = {
    Facilities.CLIMBING: "Climbing Wall",
    Facilities.FITNESS: "Fitness Room",
    Facilities.HALL: "Sports Hall",
    Facilities.POOL: "Swimming Pool",
    Facilities.SQUASH: "Squash Courts",
    Facilities.STUDIO: "Studio",
}


# Needed to create a many to many relationship for tracking users per session.
user_session_m2m = db.Table(
    "user_sessions",
    sqla.Column("user_id", sqla.ForeignKey("user.user_id"), primary_key=True),
    sqla.Column("session_id", sqla.ForeignKey("session.session_id"), primary_key=True),
)


# inherits required params, methods for flask_login
class User(db.Model, UserMixin):
    user_id = sqla.Column(sqla.Integer, primary_key=True)
    username = sqla.Column(sqla.String, unique=True)
    password = sqla.Column(sqla.String)
    email = sqla.Column(sqla.String)
    role = sqla.Column(Enum(Roles))
    membership = sqla.Column(Enum(Membership), default=Membership.NONE)
    membership_expiration_date = sqla.Column(sqla.DateTime)

    sessions = db.relationship("Session", secondary=user_session_m2m, backref="users")

    # Links to a stripe Customer object
    stripe_id = sqla.Column(sqla.String)

    def get_id(self):
        return str(self.user_id)

    def get_by_id(user_id: str) -> "User":
        """
        Returns a User object if user_id is valid else None
        """
        return db.session.execute(select(User).where(User.user_id == user_id)).scalar()

    def display_membership_type(self):
        if self.membership == Membership.NONE:
            return "None"
        if self.membership == Membership.MONTH:
            return "Month"
        if self.membership == Membership.YEAR:
            return "Year"

    def admin_data(self):
        if self.role == Roles.CUSTOMER:
            return {
                "id": self.user_id,
                "username": self.username,
                "email": self.email,
                "stripe_id": self.stripe_id,
            }
        else:
            return {
                "id": self.user_id,
                "username": self.username,
                "role": self.role,
            }


class Facility(db.Model):
    id = sqla.Column(sqla.Integer, primary_key=True)
    facility_id = sqla.Column(Enum(Facilities))
    start_time = sqla.Column(sqla.Time)
    end_time = sqla.Column(sqla.Time)
    max_capacity = sqla.Column(sqla.Integer)

    def admin_data(self):
        return {
            "id": self.id,
            "facility_id": self.facility_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "max_capacity": self.max_capacity,
        }


class Session(db.Model):
    session_id = sqla.Column(sqla.Integer, primary_key=True)
    session_type = sqla.Column(Enum(Activities))
    facility_id = sqla.Column(Enum(Facilities))
    start_time = sqla.Column(sqla.DateTime)
    end_time = sqla.Column(sqla.DateTime)
    is_class = sqla.Column(sqla.Integer)

    # Also has a Session.users - a list of users who have booked the session
    def __repr__(self):
        return f"<Session Type: {self.session_type}, at {Facilities(self.facility_id)} from: {self.start_time} to: {self.end_time}>"

    def display_facility(self):
        return facil_to_str[self.facility_id]

    def display_session_type(self):
        return act_to_str[self.session_type]

    def display_date(self):
        return self.start_time.strftime("%a %d %b")

    def display_start_time(self):
        return self.start_time.strftime("%H:%M")

    def display_end_time(self):
        return self.end_time.strftime("%H:%M")

    def unique_code(self):
        return (
            str(self.session_type.value)
            + "-"
            + str(self.facility_id.value)
            + "-"
            + self.start_time.strftime("%d/%m/%y-%H")
            + "-"
            + self.end_time.strftime("%H")
        )

    def from_unique_code(code):
        print(code)
        sections = code.split("-")
        s = Session()
        s.session_type = Activities(int(sections[0]))
        s.facility_id = Facilities(int(sections[1]))
        s.start_time = datetime.datetime.strptime(
            sections[2] + "/" + sections[3], "%d/%m/%y/%H"
        )
        s.end_time = datetime.datetime.strptime(
            sections[2] + "/" + sections[4], "%d/%m/%y/%H"
        )
        return s

    def to_dict(self):
        return {
            "session_type": self.session_type.value,
            "facility_id": self.facility_id.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "is_class": self.is_class,
            "session_code": self.unique_code(),
        }

    def toJSON(self):
        d = {
            "session_type": self.session_type.value,
            "facility_id": self.facility_id.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "is_class": self.is_class,
        }
        return json.dumps(d)

    def fromJSON(self, data):
        data = json.loads(data)
        self.session_type = Activities(data["session_type"])
        self.facility_id = Facilities(data["facility_id"])
        self.start_time = datetime.datetime.fromisoformat(data["start_time"])
        self.end_time = datetime.datetime.fromisoformat(data["end_time"])
        self.is_class = data["is_class"]


class Activity(db.Model):
    activity_id = sqla.Column(sqla.Integer, primary_key=True)
    activity_type = sqla.Column(Enum(Activities))
    facility_id = sqla.Column(Enum(Facilities))
    day = sqla.Column(Enum(Days))
    start_time = sqla.Column(sqla.Time)
    end_time = sqla.Column(sqla.Time)

    def __repr__(self) -> str:
        return f"<Activity Type: {self.activity_type} At: {self.facility_id} on {self.day} - {self.start_time}-{self.end_time}>"

    def display_facility(self):
        return facil_to_str[self.facility_id]

    def display_activity_type(self):
        return act_to_str[self.activity_type]

    def data(self):
        return [
            self.activity_id,
            self.activity_type.name,
            self.facility_id.name,
            self.day.name,
            self.start_time,
            self.end_time,
        ]

    def admin_data(self):
        return {
            "id": self.activity_id,
            "activity_type": self.activity_type.name,
            "facility_id": self.facility_id.name,
            "day": self.day.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class Statistics(db.Model):
    year = sqla.Column(sqla.Integer, primary_key=True)
    members = sqla.Column(sqla.Integer)
    trainers = sqla.Column(sqla.Integer)
    sales = sqla.Column(sqla.Integer)
