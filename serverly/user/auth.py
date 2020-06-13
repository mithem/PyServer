"""
serverly.user.auth
---
Some useful functions for authentication of users

Customization
--
Attribute | Description
- | - 
USER_NOT_FOUND_TMPLT: str | Template with access to the UserNotFoundError `e`.
UNAUTHORIZED_TMPLT: str | Template for unauthorized access.
"""


import datetime
import string
from functools import wraps
from typing import Union

import serverly
import serverly.user.session
import serverly.utils
from serverly.objects import Request, Response
from serverly.user import (BearerToken, User, require_verified)
from serverly.user.err import NotAuthorizedError, UserNotFoundError

# use these to customize the response of built-in authentication functions like the basic_auth()-decorator
USER_NOT_FOUND_TMPLT = "User $e"
UNAUTHORIZED_TMPLT = "Unauthorized."


def basic_auth(func):
    """Use this as a decorator to specify that serverly should automatically look for the (via 'Basic') authenticated user inside of the request object. You can then access the user with request.user. If the user is not authenticated, not found, or another exception occurs, your function WILL NOT BE CALLED."""
    @wraps(func)
    def wrapper(request: Request, *args, **kwargs):
        try:
            if request.auth_type.lower() == "basic":
                request.user = serverly.user.get(request.user_cred[0])
                serverly.user.authenticate(
                    request.user_cred[0], request.user_cred[1], True, require_verified)
            else:
                raise NotAuthorizedError("Not authenticated.")
        except (AttributeError, NotAuthorizedError) as e:
            s = {"e": str(e)}
            if e.__class__ == AttributeError:
                header = {"www-authenticate": "basic"}
            else:
                header = {}
                try:
                    s = {
                        **serverly.user.get(request.user_cred[0]).to_dict(), **s}
                except:
                    s = {}
            temp = string.Template(UNAUTHORIZED_TMPLT)
            msg = temp.safe_substitute(s)
            return Response(401, header, msg)
        except UserNotFoundError as e:
            temp = string.Template(USER_NOT_FOUND_TMPLT)
            msg = temp.safe_substitute(
                e=str(e))
            return Response(404, body=msg)
        except Exception as e:
            serverly.logger.handle_exception(e)
            return Response(500, body=f"We're sorry, it seems like serverly, the framework behind this server has made an error. Please advise the administrator about incorrect behaviour in the 'basic_auth'-decorator. The specific error message is: {str(e)}")
        return func(request, *args, **kwargs)
    return wrapper


def bearer_auth(scope: Union[str, list], expired=True):
    """This decorator allows you to specify that your function requires the user to have an specific scope (or higher of course). `scope` can be of type str or list<str>.

    `expired`: bool specifies whether to handle expired tokens appropriately (-> not authorized).
    """
    def my_wrap(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                if request.auth_type == None:
                    return Response(401, {"www-authenticate": "bearer"}, UNAUTHORIZED_TMPLT)
                if request.auth_type.lower() == "bearer":
                    token = request.user_cred
                    if token == None or token == "":
                        return Response(401, {"www-authenticate": "bearer"}, UNAUTHORIZED_TMPLT)
                    request.user = serverly.user.get_by_token(
                        token, True, expired, scope)
                    return func(request, *args, **kwargs)
                else:
                    return Response(401, {"www-authenticate": "bearer"}, UNAUTHORIZED_TMPLT)
            except (AttributeError, NotAuthorizedError, UserNotFoundError) as e:
                return Response(401, body=UNAUTHORIZED_TMPLT)
            except Exception as e:
                serverly.logger.handle_exception(e)
                return Response(500, body=f"We're sorry, it seems like serverly, the framework behind this server has made an error. Please advise the administrator about incorrect behaviour in the 'bearer_auth'-decorator. The specific error message is: {str(e)}")
        return wrapper
    return my_wrap


def session_auth(scope: Union[str, list]):
    """Use this decorator to authenticate the user by the latest session. Uses `bearer_auth`."""
    def my_wrap(func):
        @wraps(func)
        @bearer_auth(scope)
        def wrapper(request: Request, *args, **kwargs):
            unauth_res = string.Template(
                UNAUTHORIZED_TMPLT).safe_substitute(**request.user.to_dict())
            try:
                last_session = serverly.user.session.get_last_session(
                    request.user.username)
                print(last_session.end)
                d = datetime.datetime.now()
                print(d)
                if last_session.end + datetime.timedelta(seconds=serverly.user.session_renew_threshold) < d:
                    return Response(401, body=unauth_res)
            except Exception as e:
                serverly.logger.handle_exception(e)
                return Response(500, body=str(e))
            return func(request, *args, **kwargs)
        return wrapper
    return my_wrap


@serverly.user._setup_required
def valid_token(bearer_token: Union[str, BearerToken], expired=True, scope: Union[str, list] = None):
    """Return whether token is valid. If `expired`, also check whether it's expired and return False if it is."""
    try:
        session = serverly.user._Session()
        if type(bearer_token) == str:
            token: BearerToken = session.query(
                BearerToken).filter_by(value=bearer_token).first()
        else:
            token: BearerToken = bearer_token
        if token == None:
            return False
        if token.expires == None:
            expired = False
        b = token.expires > datetime.datetime.now() if expired else True
        if type(scope) == str:
            scope = [scope]
        scopes = serverly.utils.parse_scope_list(token.scope)
        c = True
        if scope != [""] and scope != "" and scope != None:
            try:
                for s in scope:
                    assert s in scopes
            except AssertionError:
                c = False
        return token != None and b and c
    except Exception as e:
        serverly.logger.handle_exception(e)
        return False


@serverly.user._setup_required
def clear_expired_tokens():
    """Delete (permanently) all BearerTokens which are expired and return how many where deleted."""
    try:
        session = serverly.user._Session()
        tokens = session.query(BearerToken).filter(
            BearerToken.expires.isnot(None))
        n = datetime.datetime.now()
        i = 0
        for token in tokens:
            if token.expires < n:
                session.delete(token)
                i += 1
        session.commit()
        return i
    except Exception as e:
        serverly.logger.handle_exception(e)
        return -1


@serverly.user._setup_required
def get_tokens_by_user(username: str):
    """Return a list of all BearerToken objects corresponding to a user."""
    try:
        session = serverly.user._Session()
        tokens = session.query(BearerToken).filter_by(username=username).all()
        session.close()
        return tokens
    except Exception as e:
        serverly.logger.handle_exception(e)
        return []


@serverly.user._setup_required
def get_new_token(username: str, scope: Union[str, list] = [], expires: Union[datetime.datetime, str] = None):
    """Generate a new token, save it for `username` and return it (obj)."""
    try:
        if type(expires) == str:
            expires = datetime.datetime.fromisoformat(expires)

        session = serverly.user._Session()
        token = BearerToken()
        token.username = str(username)
        token.scope = serverly.utils.get_scope_list(scope)
        token.expires = expires
        # oh yeah! ~9.6x10^59 ages of the universe at 1 trillion guesses per second
        token.value = serverly.utils.ranstr(50)

        session.add(token)

        session.commit()
        return token
    except Exception as e:
        serverly.logger.handle_exception(e)
        return None


@serverly.user._setup_required
def get_all_tokens():
    session = serverly.user._Session()
    result = session.query(BearerToken).all()
    session.close()
    return result


@serverly.user._setup_required
def clear_all_tokens():
    """Delete ALL tokens. Be careful, cause you might break a lot of logins."""
    session = serverly.user._Session()
    session.query(BearerToken).delete()
    session.commit()
    session.close()
