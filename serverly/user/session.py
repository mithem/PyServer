import datetime

import serverly
import sqlalchemy
from serverly.user import Session, _setup_required


@_setup_required
def get_all_sessions(username: str):
    """Return all sessions for `username`. `username`= None -> Return all sessions of all users"""
    session = serverly.user._Session()
    result = session.query(Session).filter_by(username=username).all() if type(
        username) == str else session.query(Session).all()
    session.close()
    return result


@_setup_required
def get_last_session(username: str):
    session = serverly.user._Session()
    result: Session = session.query(
        Session).filter_by(username=username).order_by(sqlalchemy.desc(Session.id)).first()
    session.close()
    return result


@_setup_required
def extend_session(id, new_end: datetime.datetime):
    session = serverly.user._Session()
    s: Session = session.query(Session).filter_by(id=id).first()
    s.end = new_end
    session.commit()
    session.close()


@_setup_required
def new_activity(username: str, address: tuple):
    """Update sessions to reflect a new user activity"""
    def create_new():
        session = serverly.user._Session()
        new = Session()
        new.username = username
        new.start = n
        new.end = n + \
            datetime.timedelta(seconds=serverly.user.session_renew_threshold)
        new.address = f"{address[0]}:{address[1]}"
        session.add(new)
        session.commit()
    n = datetime.datetime.now()
    last = get_last_session(username)
    try:
        if last.end + datetime.timedelta(seconds=serverly.user.session_renew_threshold) > n:
            extend_session(last.id, n)
        else:
            create_new()
    except AttributeError as e:
        create_new()
    except Exception as e:
        serverly.logger.handle_exception(e)


@_setup_required
def delete_sessions(username: str):
    """Delete all sessions of `username`. Set to None to delete all sessions. Non-revokable."""
    session = serverly.user._Session()
    if username == None:
        session.query(Session).delete()
    else:  # is that necessary?
        session.query(Session).filter_by(username=username).delete()
    session.commit()
