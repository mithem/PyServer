"""This module holds the serverly standard API. This allows you to just specify endpoints while serverly takes care of the actual API for registering users, etc.).

See the Postman documentation online: https://documenter.getpostman.com/view/10720102/Szf549XF?version=latest
"""
import string
from functools import wraps

import serverly
import serverly.user
import serverly.utils
from serverly import Request, Response, error_response
from serverly.user import basic_auth, bearer_auth, err, requires_role

_RES_406 = Response(
    406, body="Unable to parse required parameters. Expected username, password.")
verify_mail = False
only_user_verified = False
use_sessions = False
persistant_user_attributes = []
_reversed_api = {}


def use(function: str, method: str, path: str):
    """Serverly comes with builtin API-functions for the following serverly.user functions:
    - authenticate: Basic
    - change: Basic
    - delete: Basic
    - get: Basic
    - register: None
    - sessions.post: Basic (Create new session or append to existing one)
    - sessions.get: Basic (Get all sessions of user)
    - sessions.delete: Basic (Delete all sessions of user)
    - bearer.authenticate: Bearer (Authenticate user with Bearer token)
    - bearer.new: Basic (Send a new Bearer token to user authenticated via Basic)
    - console.index: Basic (Entrypoint for serverly's admin console)
    - console.users: Basic (users overview)
    - console.summary.users: Basic (API for getting a summary of all users)
    `function`accepts on of the above. The API-endpoint will be registered for `method`on `path`.
    All console functions require the 'admin' role.
    """
    global verify_mail
    supported_funcs = {
        "authenticate": _api_authenticate,
        "change": _api_change,
        "delete": _api_delete,
        "get": _api_get,
        "register": _api_register,
        "sessions.post": _api_sessions_post,
        "sessions.get": _api_sessions_get,
        "sessions.delete": _api_sessions_delete,
        "bearer.authenticate": _api_bearer_authenticate,
        "bearer.new": _api_bearer_new,
        "bearer.clear": _api_bearer_clear,
        "console.index": _console_index,
        "console.users": _console_users,
        "console.summary.users": _console_summary_users
    }
    if not function.lower() in supported_funcs.keys():
        raise ValueError(
            "function not supported. Supported are " + ", ".join(supported_funcs.keys()) + ".")
    func = supported_funcs[function.lower()]
    serverly._sitemap.register_site(
        method, func, path)
    _reversed_api[func.__name__] = path


def setup(mail_verification=False, require_user_to_be_verified=False, use_sessions_when_client_calls_endpoint=False, fixed_user_attributes=[]):
    """Use `mail_verification` to control whether the register function should automatically try to verify the users' email. You can also manually do that by calling `serverly.user.mail.send_verification_email()`.

    If `require_user_to_be_verified`, users will only authenticate if their email is verified.

    If `use_sessions_when_client_calls_endpoint`, a new user activity will automatically be registered if the client uses an endpoint.

    `fixed_user_attributes` is a list which contains the attribute names of User attributes which may not be changed by the API. Useful for roles and other attributes clients may not change (via API).
    """
    global verify_mail, only_user_verified, use_sessions, persistant_user_attributes
    verify_mail = mail_verification
    only_user_verified = require_user_to_be_verified
    use_sessions = use_sessions_when_client_calls_endpoint
    persistant_user_attributes = fixed_user_attributes


def _check_to_use_sessions(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if use_sessions:
            serverly.user.new_activity(request.user.username, request.address)
        return func(request, *args, **kwargs)
    return wrapper


def _get_content(base: str):
    return string.Template(base).safe_substitute(**_reversed_api)


@basic_auth
@_check_to_use_sessions
def _api_authenticate(req: Request):
    return Response()


@basic_auth
@_check_to_use_sessions
def _api_change(req: Request):
    new = {}
    for k, v in req.obj.items():
        if k not in persistant_user_attributes:
            new[k] = v
    serverly.user.change(req.user_cred[0], **new)
    return Response()


@basic_auth
@_check_to_use_sessions  # lol
def _api_delete(req: Request):
    serverly.user.delete(req.user.username)
    return Response()


@basic_auth
@_check_to_use_sessions
def _api_get(req: Request):
    return Response(body=serverly.utils.clean_user_object(req.user))


def _api_register(req: Request):  # cannot use _check_to_use_sessions as it needs a user obj
    try:
        serverly.user.register(**req.obj)
        response = Response()
        serverly.user.new_activity(req.obj["username"], req.address)
        if verify_mail:
            serverly.user.mail.manager.schedule_verification_mail(
                req.obj["username"])
    except (KeyError, AttributeError, TypeError) as e:
        serverly.logger.handle_exception(e)
        response = _RES_406
    except err.UserAlreadyExistsError as e:
        response = Response(406, body=str(e))
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


@basic_auth
def _api_sessions_post(req: Request):
    serverly.user.new_activity(req.user.username, req.address)
    return Response()


@basic_auth
@_check_to_use_sessions
def _api_sessions_get(req: Request):
    ses = serverly.user.get_all_sessions(req.user.username)
    sessions = [s.to_dict()
                for s in ses]
    response = Response(body=sessions)
    return response


@basic_auth
def _api_sessions_delete(req: Request):
    serverly.user.delete_sessions(req.user.username)
    return Response()


@bearer_auth
@_check_to_use_sessions
def _api_bearer_authenticate(request: Request):
    return Response()


@basic_auth
@_check_to_use_sessions
def _api_bearer_new(request: Request):
    token = serverly.user.get_new_token(request.user.username, request.obj.get(
        "scope", []), request.obj.get("expires"))
    serverly.logger.context = "bearer"
    return Response(body={"token": token.to_dict()})


@basic_auth
@_check_to_use_sessions
def _api_bearer_clear(request: Request):
    n = serverly.user.clear_expired_tokens()
    return Response(body=f"Deleted {n} expired tokens.")


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_index(request: Request):
    content = _get_content(serverly.default_sites.console_index)
    return Response(body=content)


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_users(request: Request):
    content = _get_content(serverly.default_sites.console_users)
    return Response(body=content)


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_summary_users(request: Request):
    users = serverly.user.get_all()

    n_users = len(users)
    n_emails = 0
    n_verified = 0

    for user in users:
        n_emails += 1 if user.email != None else 0
        n_verified += 1 if user.verified != None else 0

    return Response(body=f"There are {n_users} users with {n_emails} emails, {n_verified} of which are verified.")
