"""This module holds the serverly standard API. This allows you to just specify endpoints while serverly takes care of the actual API for registering users, etc.).

See the Postman documentation online: https://documenter.getpostman.com/view/10720102/Szf549XF?version=latest
"""
import serverly
import serverly.utils
from serverly import Request, Response, error_response
from serverly.user import err
from serverly.user import basic_auth, bearer_auth
import serverly.user
from functools import wraps

_RES_406 = Response(
    406, body="Unable to parse required parameters. Expected username, password.")
verify_mail = False
only_user_verified = False
use_sessions = False


def use(function: str, method: str, path: str, mail_verification=False, require_user_to_be_verified=False, use_sessions_when_client_calls_endpoint=False):
    """Serverly comes with builtin API-functions for the following serverly.user functions:
    - authenticate: Basic
    - change: Basic
    - delete: Basic
    - get: Basic
    - register: None
    - sessions.post: Basic (create new session or append to existing one)
    - sessions.get: Basic (get all sessions of user)
    - sessions.delete: Basic (delete all sessions of user)
    - bearer.authenticate: Bearer (authenticate user with Bearer token)
    - bearer.new: Basic (Send a new Bearer token to user authenticated via Basic)
    `function`accepts on of the above. The API-endpoint will be registered for `method`on `path`.

    Use `mail_verification` to control whether the register function should automatically try to verify the users' email. You can also manually do that by calling `serverly.user.mail.send_verification_email()`.

    If `require_user_to_be_verified`, users will only authenticate if their email is verified.

    If `use_sessions_when_client_calls_endpoint`, a new user activity will automatically be registered if the client uses an endpoint.
    """
    global verify_mail
    supported_funcs = {"authenticate": _api_authenticate, "change": _api_change,
                       "delete": _api_delete, "get": _api_get, "register": _api_register, "sessions.post": _api_sessions_post, "sessions.get": _api_sessions_get, "sessions.delete": _api_sessions_delete, "bearer.authenticate": _api_bearer_authenticate, "bearer.new": _api_bearer_new}
    if not function.lower() in supported_funcs.keys():
        raise ValueError(
            "function not supported. Supported are " + ", ".join(supported_funcs.keys()) + ".")
    serverly._sitemap.register_site(
        method, supported_funcs[function.lower()], path)

    global verify_mail, only_user_verified, use_sessions

    if mail_verification:
        verify_mail = True
    if require_user_to_be_verified:
        only_user_verified = True
    if use_sessions_when_client_calls_endpoint:
        use_sessions = True


def _check_to_use_sessions(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if use_sessions:
            serverly.user.new_activity(request.user.username, request.address)
        return func(request, *args, **kwargs)
    return wrapper


@basic_auth
@_check_to_use_sessions
def _api_authenticate(req: Request):
    return Response()


@basic_auth
@_check_to_use_sessions
def _api_change(req: Request):
    serverly.user.change(req.user_cred[0], **req.obj)
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
    token = serverly.utils.ranstr(50)
    serverly.user.change(request.user.username, bearer_token=token)
    return Response(body={"token": token})
