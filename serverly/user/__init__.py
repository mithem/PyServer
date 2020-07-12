"""
serverly.user
--
Configuration
--
Attribute | Description
- | -
session_renew_threshold = 60 | Number of seconds after which a new session will be created instead of increasing the end date (used by `serverly.user.session` and `serverly.user.auth`)

"""
import datetime
import hashlib
import string
from functools import wraps
from hmac import compare_digest
from typing import Union

import serverly
import sqlalchemy
from serverly.err import (ConfigurationError, NotAuthorizedError,
                          UserAlreadyExistsError, UserNotFoundError)
from serverly.objects import DBObject, Request, Response
from serverly.utils import get_scope_list, parse_scope_list, ranstr
from sqlalchemy import (Binary, Boolean, Column, DateTime, Float, Integer,
                        Interval, String)
from sqlalchemy.ext.declarative import declarative_base

session_renew_threshold = 60

_required_user_attrs = []
_role_hierarchy = {}
_engine = None
_Session: sqlalchemy.orm.Session = None
algorithm = None
salting = 1
require_verified = False


Base = declarative_base()


class User(Base, DBObject):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True)
    password = Column(String)
    salt = Column(String)

    def __str__(self):
        result = "<User("
        for i in dir(self):
            if not i.startswith("_") and not i.endswith("_") and not callable(getattr(self, i)) and i != "metadata":
                result += i + "=" + str(getattr(self, i)) + ", "
        result = result[:-2] + ")>"
        return result


class Session(Base, DBObject):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    start = Column(DateTime)
    end = Column(DateTime)
    address = Column(String)

    @property
    def length(self):
        """Timedelta object of the session"""
        result: datetime.timedelta = self.end - self.start
        return result

    def __str__(self):
        return f"<Session(username={self.username}, start={str(self.start)}, end={str(self.end)}, length={str(self.length)}, address={self.address})"


class BearerToken(Base, DBObject):
    __tablename__ = "bearer_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expires = Column(DateTime)
    # custom seperators (;) have to be used as the SQLAlchemy-backend doesn't support lists in every SQL flavor
    scope = Column(String)
    username = Column(String)
    value = Column(String, unique=True)


def mockup_hash_algorithm(data: bytes):
    """A hashlib-like function that doesn't hash your content at all."""
    class HashOutput:
        def __init__(self, data: bytes):
            self.data = data

        def hexdigest(self):
            return str(self.data, "utf-8")
    return HashOutput(data)


def setup(hash_algorithm=hashlib.sha3_512, use_salting=True, filename="serverly_users.db", user_columns={}, verbose=False, require_email_verification=False, role_hierarchy={}, debug=False):
    """

    :param hash_algorithm:  (Default value = hashlib.sha3_512) Algorithm used to hash passwords (and salts if specified). Needs to work like hashlib's: algo(bytes).hexadigest() -> str.
    :param use_salting:  (Default value = True) Specify whether to use salting to randomise the hashes of password. Makes it a bit more secure.
    :param filename:  (Default value = "serverly_users.db") Filename of the SQLite database.
    :param user_columns:  (Default value = {}) Attributes of a user, additionally to `id`, `username`, `password`and `salt` (which will not be used if not specified so). You can use tuples to specify a default value in the second item.

    Example:

    ```python
    {
        'first_name': str,
        'last_name': str,
        'email': str,
        'birth_year': int,
        'gdp': float,
        'newsletter': (bool, False),
        'verified': (bool, False)
    }
    ```
    Supported types are str, float, int, bytes, bool, datetime.datetime, datetime.timedelta.
    :param verbose:  (Default value = True) Verbose mode of the SQLite engine
    :param require_email_verification: require that the email of the user is verified when authenticating. Has no effect on the `authenticate`-method but on the `basic_auth`-decorator for example.
    :param role_hierarchy: a dictionary with roles as keys & values. If an endpoint requires a role the user does not have explicitly, the user will be authorized if his 'subroles' match de required one(s).

    Example:

    ```python
    {
        'normal': 'normal', # required
        'admin': 'normal',
        'staff': 'normal'
        'root': 'admin'
    }
    ```
    Now, admins & staff have the same rights as normals, root has the same as admin & staff (and therefore normals), but you can still decide to require 'admin' for some endpoint.
    :param debug: Debug mode (Just prints out the configuration)
    """
    global _engine
    global _Session
    global algorithm
    global salting
    global require_verified
    global _role_hierarchy

    python_types_to_sqlalchemy_types = {
        str: String,
        float: Float,
        int: Integer,
        bytes: Binary,
        bool: Boolean,
        datetime.datetime: DateTime,
        datetime.timedelta: Interval
    }
    for attribute_name, python_type in user_columns.items():
        try:
            if type(python_type) != tuple:
                setattr(User, attribute_name, Column(
                    python_types_to_sqlalchemy_types[python_type]))
            else:
                setattr(User, attribute_name, Column(
                    python_types_to_sqlalchemy_types[python_type[0]], default=python_type[1]))
        except KeyError:
            raise TypeError(f"'{str(python_type)}' not supported.'")

    algorithm = hash_algorithm
    salting = int(use_salting)
    _engine = sqlalchemy.create_engine("sqlite:///" + filename, echo=verbose)
    Base.metadata.create_all(bind=_engine)
    _Session = sqlalchemy.orm.sessionmaker(bind=_engine)
    require_verified = require_email_verification

    for attr in _required_user_attrs:
        if getattr(User, attr, "definetely not a value") == "definetely not a value":
            raise ConfigurationError(f"User does not have attribute '{attr}'")

    _role_hierarchy = serverly.utils.parse_role_hierarchy(role_hierarchy)

    serverly.logger.context = "setup"
    serverly.logger.debug(
        f"serverly.user is now set up with the following configuration:\nalgorithm: {hash_algorithm.__name__}\nsalting: {bool(salting)}\nrequire email verification: {require_email_verification}\nrole hierarchy: {_role_hierarchy}", debug)


def _setup_required(func):
    """internal decorator to apply when db setup is required before running the function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _engine == None:
            setup()
        return func(*args, **kwargs)
    return wrapper


def _requires_user_attr(attribute: str):
    """Internal decorator to raise Exception if user does not have a required attribute."""
    def my_wrap(func):
        global _required_user_attrs
        _required_user_attrs.append(str(attribute))

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return my_wrap


@_setup_required
def register(username: str, password: str, **kwargs):
    try:
        if username == None:
            raise ValueError("username expected.")
        if password == None:
            raise ValueError("password expected.")

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
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


@_setup_required
def authenticate(username: str, password: str, strict=False, verified=False):
    """Return True or False. If `strict`, raise `NotAuthorizedError`. If `verified`, the user also has to be verified (requires email)"""
    session = _Session()
    req_user = get(username, strict)
    try:
        result = compare_digest(req_user.password, algorithm(
            bytes(req_user.salt * salting + str(password), "utf-8")).hexdigest())
    except:
        return False
    if verified:
        result = result and req_user.verified
    if strict:
        if result:
            return True
        else:
            raise NotAuthorizedError
    return result


@_setup_required
def get(username: str, strict=True):
    """Get user, authenticated by username. If `strict` (default), raise UserNotFoundError if user does not exist. Else return None."""
    session = _Session()
    result: User = session.query(User).filter_by(username=username).first()
    session.close()
    if result == None and strict:
        raise UserNotFoundError(f"'{username}' not found.")
    return result


@_setup_required
def has_role(roles: Union[str, list]) -> bool:
    """Return bool whether there is at least 1 user with role(s)"""
    if type(roles) == str:
        roles = [roles]
    users = serverly.user.get_all()
    for u in users:
        for role in roles:
            if u.role == role or u.role in _role_hierarchy[u.role]:
                return True
    return False


@_setup_required
def get_by_email(email: str, strict=True):
    """Get user with `email`. If `strict` (default), raise UserNotFoundError if user does not exist. Else return None."""
    session = _Session()
    result: User = session.query(User).filter_by(email=email).first()
    session.close()
    if result == None and strict:
        raise UserNotFoundError(f"User with email '{email}' not found.")
    return result


@_setup_required
def get_by_token(bearer_token: Union[str, BearerToken], strict=True, expired=True, scope: Union[str, list] = None):
    """Get user associated with `bearer_token`. If `strict`(default), raise UserNotFoundError if user does not exist. Else return None. If `expired` (default), treat user as unauthorized if token is expired."""
    session = _Session()
    if type(bearer_token) == str:
        token: BearerToken = session.query(
            BearerToken).filter_by(value=bearer_token).first()
    else:
        token: BearerToken = bearer_token
    if expired:
        if strict:
            c = serverly.user.auth.valid_token(token, expired, scope)
            if not c:
                raise NotAuthorizedError("Not authorized.")
    result: User = session.query(User).filter_by(
        username=token.username).first()
    session.close()
    if result == None and strict:
        raise UserNotFoundError("No user with token found.")
    return result


@_setup_required
def get_by_id(identifier: int, strict=True):
    """Get user with `identifier` (id). If `strict`(default), raise UserNotFoundError if user does not exist. Else return None."""
    session = _Session()
    result: User = session.query(User).filter_by(id=identifier).first()
    session.close()
    if result == None and strict:
        raise UserNotFoundError(f"User with id {id} not found.")
    return result


@_setup_required
def get_all():
    """Return a list of all user objects in the database."""
    session = _Session()
    result = session.query(User).all()
    session.close()
    return result


@_setup_required
def change(username: str, new_username: str = None, password: str = None, **kwargs):
    try:
        important_attributes = ["username", "password", "salt", "id"]
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
        to_delete = []
        for key, value in update_dict.items():
            k = str(key).replace("User.", "")
            if value == None and k in important_attributes:
                to_delete.append(key)
        for i in to_delete:
            del update_dict[i]
        session.query(User).update(update_dict)
        session.commit()
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


@_setup_required
def delete(username: str):
    """Delete user permanently."""
    session = _Session()
    session.delete(get(username))
    session.commit()
    session.close()


@_setup_required
def delete_all():
    """Delete all users permanently."""
    session = _Session()
    session.query(User).delete()
    session.commit()
    session.close()


@_requires_user_attr("role")
def requires_role(role: Union[str, list]):
    """Use this decorator to authenticate the user by their `role`- attribute. Requires the use of another authentication decorator before this one."""
    role = [r.lower() for r in role] if type(role) == list else role.lower()

    def my_wrap(func):
        @wraps(func)
        def wrapper(request: Request, *args, **kwargs):
            user_roles = _role_hierarchy.get(request.user.role, set())
            if type(role) == list:
                for r in role:
                    if r == request.user.role or r in user_roles:
                        return func(request, *args, **kwargs)
            if type(role) == str:
                if role == request.user.role or role in user_roles:
                    return func(request, *args, **kwargs)
            return Response(401, body=string.Template(UNAUTHORIZED_TMPLT).safe_substitute(**request.user.to_dict()))
        return wrapper
    return my_wrap
