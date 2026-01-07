import datetime
from app.models import (
    Activities,
    Activity,
    Days,
    Session,
    act_to_str,
    facil_to_str,
    Facility,
)
from sqlalchemy import select
from app import db
from flask_login import current_user
import json


class CalanderItem:
    def __init__(self, date: datetime.date, type="general") -> None:
        """
        A class that generates items that can be displayed as some kind of calander to help the user book a session.
        params:
            date: The date to generate activities for.
            type: One of 'general', 'class', 'team', 'all'. Filters the returned results.
        """
        self.date = date
        self.weekday = date.weekday()
        self.activities = []
        self.type = type
        self.filters = {
            "general": [
                Activities.GENERAL,
                Activities.LANESWIM,
                Activities.SWIMLESSON,
            ],
            "class": [Activities.AEROBICS, Activities.YOGA, Activities.PILATES],
            "team": [Activities.TEAM],
            "all": list(Activities),
        }
        self.filter = self.filters[type]
        self.activities = (
            db.session.execute(
                select(Activity).where((Activity.day == Days(self.weekday)))
            )
            .scalars()
            .all()
        )

    def generate_sessions(
        self, activity: Activity, session_length: int
    ) -> "list[Session]":
        """
        Returns a list of session objects for a given activity.
        session_length specifies the length (in hours) of the sessions
        """
        sessions = []
        for i in range(
            activity.start_time.hour, activity.end_time.hour, session_length
        ):
            s = Session(
                session_type=activity.activity_type,
                facility_id=activity.facility_id,
                start_time=datetime.datetime(
                    self.date.year, self.date.month, self.date.day, i
                ),
                end_time=datetime.datetime(
                    self.date.year, self.date.month, self.date.day, i + session_length
                ),
                is_class=0,
            )
            sessions.append(s)

        sessions = self.remove_invalid_sessions(sessions)
        return sessions

    @staticmethod
    def remove_invalid_sessions(sessions: "list[Session]"):
        """
        Removes sessions that a user cannot attend due to clashes with already booked sessions.
        """
        booked_sessions = [s.unique_code() for s in current_user.sessions]

        # Users has no booked sessions
        if not booked_sessions:
            return sessions

        times = [[sess.start_time, sess.end_time] for sess in current_user.sessions]
        unavailable_times = merge_session_times(times)

        bad_sessions = []
        for sess in sessions:
            # Remove sessions that the user cannot attend
            for un in unavailable_times:
                if un[0] <= sess.start_time < un[1]:
                    bad_sessions.append(sess)

            # Remove sessions for times when the user is busy.
        return [s for s in sessions if s not in bad_sessions]

    def create__dicts_from_activities(self) -> "list[dict]":
        """
        Creates a dict for each activity on self.date along with a list of bookable sessions.
        Intended to be passed to a template for front-end use.
        """
        activity_dicts = []
        for act in self.activities:
            # filter returned activties so we can reuse this for other views.
            if act.activity_type not in self.filter:
                continue

            if act.activity_type == Activities.TEAM:
                sessions = self.generate_sessions(activity=act, session_length=2)

            # Generate slots for each activity
            else:
                sessions = self.generate_sessions(activity=act, session_length=1)

            a = {
                "id": act.activity_id,
                "date": self.date.isoformat(),
                "activity": act_to_str[act.activity_type],
                "facility": facil_to_str[act.facility_id],
                "start_time": act.start_time,
                "end_time": act.end_time,
                "sessions": sessions,
            }
            activity_dicts.append(a)

        return activity_dicts

    def create_JSON_from_activities(self) -> "list[dict]":
        """
        Creates a dict for each activity on self.date along with a list of bookable sessions.
        Intended to be passed to a template for front-end use.
        """
        activity_dicts = []
        for act in self.activities:
            # filter returned activties so we can reuse this for other views.
            if act.activity_type not in self.filter:
                continue

            if act.activity_type == Activities.TEAM:
                sessions = self.generate_sessions(activity=act, session_length=2)

            # Generate slots for each activity
            else:
                sessions = self.generate_sessions(activity=act, session_length=1)

            a = {
                "id": act.activity_id,
                "date": self.date.isoformat(),
                "activity": act_to_str[act.activity_type],
                "facility": facil_to_str[act.facility_id],
                "start_time": act.start_time.isoformat(),
                "end_time": act.end_time.isoformat(),
                "sessions": [s.to_dict() for s in sessions],
            }
            activity_dicts.append(a)

        return json.dumps(activity_dicts)

    def generate_overview(self) -> "tuple[str, list[dict]]":
        """
        Creates a list of dicts with keys activity, facility, start_time and end_time in a user-friendly format.
        Intended for use in displaying upcoming sctivities to users.
        Returns a tuple (date, list of dicts)
        """
        # Get the activities for the given day.
        activity_dicts = self.create__dicts_from_activities()

        return (self.date.strftime("%a %d %b"), activity_dicts)


def get_overlapping_sessions(session: Session) -> "list[Session]":
    """
    Get all session that are occuring at the same time and in the same facility as a given session.
    Includes the given session.
    """
    overlapping = (
        db.session.execute(
            select(Session).where(
                (Session.start_time == session.start_time)
                & (Session.end_time == session.end_time)
                & (Session.facility_id == session.facility_id)
            )
        )
        .scalars()
        .all()
    )
    return overlapping


def get_facility_attendance(session: Session) -> "int":
    """
    Get the number of users in the same facility as session, in the same time slot
    """
    overlapping = get_overlapping_sessions(session)

    attendance = 0
    for sess in overlapping:
        attendance += len(sess.users)
    return attendance


def get_facility(session: Session) -> Facility:
    """
    Returns the Facility object of a given session
    """
    return db.session.execute(
        select(Facility).where(Facility.facility_id == session.facility_id)
    ).scalar()


def merge_session_times(
    times: "list[list[datetime.datetime]]",
) -> "list[list[datetime.datetime]]":
    """
    Takes a list of [start_time, end_time] elements and joins them to create the largest continous interval possible.
    Returns a list of [start_time, end_time] elements
    """
    times = sorted(times)
    booked_time = []
    booked_time.append(times[0])

    for time in times[1:]:
        # if current session starts between the most recent start_time and most recent end_time
        if booked_time[-1][0] <= time[0] <= booked_time[-1][1]:
            # set the most recent end_time to end_time of the current session (if larger)
            booked_time[-1][1] = max(booked_time[-1][1], time[-1])
        else:
            # can't merge this session with existing sessions.
            booked_time.append(time)
    return booked_time


def session_expired(
    session: Session, time: datetime.datetime = datetime.datetime.now()
) -> bool:
    """
    If the `start_time` of the session happened before `time` return True, else False
    """
    if session.start_time <= time:
        return True


def get_users_next_sessions(num: int = 3) -> "list[Session]":
    """
    Get a list of the users upcoming sessions.
    """

    sessions = [
        sess
        for sess in current_user.sessions
        if sess.start_time > datetime.datetime.now()
    ]
    sessions.sort(key=lambda x: x.start_time)
    return sessions[:num]


def group_session_list_by_day(sessions: "list[Session]") -> "dict":
    """
    Given a list of session object, this will return a dict of date: [Sessions]
    """
    dates = {sess.start_time.date() for sess in sessions}

    grouped = {}
    for d in dates:
        grouped.update(
            {
                d: sorted(
                    [sess for sess in sessions if sess.start_time.date() == d],
                    key=lambda x: x.start_time,
                )
            }
        )

    return grouped
