import datetime
import hashlib
from functools import wraps

import sqlalchemy
from serverly.user.err import (NotAuthenticatedError, UserAlreadyExistsError,
                               UserNotFoundError)
from serverly.utils import ranstr
from sqlalchemy import Column, Integer, String, Float, Boolean, Binary
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    salt = Column(String)

    def __str__(self):
        result = "<User("
        for i in dir(self):
            if not i.startswith("_") and not i.endswith("_"):
                result += i + "=" + str(getattr(self, i)) + ", "
        result = result[:-2] + ")>"
        return result


def mockup_hash_algorithm(data: bytes):
    """A hashlib-like function that doesn't hash your content at all."""
    class HashOutput:
        def __init__(self, data: bytes):
            self.data = data

        def hexdigest(self):
            return str(self.data, "utf-8")
    return HashOutput(data)


_engine = None
_Session = None
algorithm = None
salting = 1


def setup(hash_algorithm=hashlib.sha3_512, use_salting=True, filename="serverly_users.db", user_columns={}, verbose=True):
    """

    :param hash_algorithm:  (Default value = hashlib.sha3_512) Algorithm used to hash passwords (and salts if specified). Needs to work like hashlib's: algo(bytes).hexadigest() -> str.
    :param use_salting:  (Default value = True) Specify whether to use salting to randomise the hashes of password. Makes it a bit more secure.
    :param filename:  (Default value = "serverly_users.db") Filename of the SQLite DB.
    :param user_columns:  (Default value = {}) Attributes of a user, additionally to `id`, `username`, `password`and `salt` (which will not be used if not specified so). Example: ```python
    {
        'first_name': str,
        'last_name': str,
        'email': str,
        'birth_year': int,
        'gdp': float,
        'newsletter': bool
    }
    ```
    Supported types are str, float, int, bytes, bool.
    :param verbose:  (Default value = True)

    """
    global _engine
    global _Session
    global algorithm
    global salting

    python_types_to_sqlalchemy_types = {
        str: String,
        float: Float,
        int: Integer,
        bytes: Binary,
        bool: Boolean
    }
    for attribute_name, python_type in user_columns.items():
        try:
            setattr(User, attribute_name, Column(
                python_types_to_sqlalchemy_types[python_type]))
        except KeyError:
            raise TypeError(f"'{str(python_type)}' not supported.'")

    algorithm = hash_algorithm
    salting = int(use_salting)
    _engine = sqlalchemy.create_engine(
        "sqlite:///" + filename, echo=verbose)
    Base.metadata.create_all(bind=_engine)
    _Session = sqlalchemy.orm.sessionmaker(bind=_engine)


def _setup_required(func):
    """internal decorator to apply when db setup is required before running the function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _engine == None:
            setup()
        return func(*args, **kwargs)
    return wrapper


@_setup_required
def register(username: str, password: str, **kwargs):
    session = _Session()
    user = User()
    user.username = username
    for attname, value in kwargs.items():
        setattr(user, attname, value)
    salt = ranstr()
    user.salt = salt
    user.password = algorithm(
        bytes(salt * salting + password, "utf-8")).hexdigest()

    session.add(user)

    try:
        session.commit()
    except sqlalchemy.exc.IntegrityError:
        raise UserAlreadyExistsError(
            "User '" + username + "'" + " already exists")
    finally:
        session.close()


@_setup_required
def authenticate(username: str, password: str, strict=False):
    """return True or False. If `strict`, raise `NotAuthenticatedError`."""
    session = _Session()
    req_user = session.query(User).filter_by(username=username).first()
    try:
        result = req_user.password == algorithm(
            bytes(req_user.salt * salting + password, "utf-8")).hexdigest()
    except AttributeError:
        raise UserNotFoundError
    if strict:
        if result:
            return True
        else:
            raise NotAuthenticatedError
    return result


@_setup_required
def get(username: str):
    session = _Session()
    result = session.query(User).filter_by(username=username).first()
    session.close()
    return result


@_setup_required
def get_all():
    session = _Session()
    result = session.query(User).all()
    session.close()
    return result


@_setup_required
def change(username: str, new_username: str = None, password: str = None, **kwargs):
    session = _Session()
    user = get(username)
    update_dict = {}
    if new_username != None:
        update_dict[User.username] = new_username
    if password != None:
        update_dict[User.password] = algorithm(
            bytes(user.salt * salting + password, "utf-8")).hexdigest()
    for key, value in kwargs.items():
        update_dict[getattr(User, key)] = value
    session.query(User).update(update_dict)
    session.commit()


@_setup_required
def delete(username: str):
    session = _Session()
    session.delete(get(username))
    session.commit()
    session.close()
