"""This module holds the serverly standard API. This allows you to just specify endpoints while serverly takes care of the actual API for registering users, etc.).

See the Postman documentation online: https://documenter.getpostman.com/view/10720102/Szf549XF?version=latest
"""
import json
import mimetypes
import os
import string
from functools import wraps
from urllib import parse as parse

import serverly
import serverly.user
import serverly.user.mail
import serverly.utils
from serverly import error_response
from serverly.objects import Redirect, Request, Response
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
    - GET console.index: Basic (Entrypoint for serverly's admin console)
    - GET console.users: Basic (users overview)
    - GET console.users.change_or_register: Basic (Allows admins to change or register users on one page)
    - GET console.summary.users: Basic (API for getting a summary of all users)
    - GET console.api.user.get: Basic (get user with id defined in query). Ex. /console/api/user/get?ids=1
    - PUT console.api.user.change_or_register: Basic (API endpoint for changing or registering users)
    - POS console.api.users.verify: Basic (verify all users with ids submitted in request body)
    - POS console.api.users.deverify: Basic (same as above but deverifying users)
    - POS console.api.users.verimail: Basic (send a confirmation mail to users with ids submitted in request body)
    - DEL console.api.user.reset_password: Basic (send a password reset mail to users with ids submitted in request body)
    - DEL console.api.users.delete: Basic (delete users with ids submitted in request body)
    - POS console.api.renew_login: Basic (authenticate with admin credentials. If not successfull, sends back the WWW-Authenticate: Basic header)
    - console.all (register all available console endpoints)

    `function` accepts on of the above. The API-endpoint will be registered for `method`on `path`.
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
        "console.users.change_or_register": _console_change_or_create_user,
        "console.api.summary.users": _console_summary_users,
        "console.api.user.get": _console_api_get_user,
        "console.api.user.change_or_register": _console_api_change_or_create_user,
        "console.api.users.verify": _console_api_verify_users,
        "console.api.users.deverify": _console_api_deverify_users,
        "console.api.users.verimail": _console_api_verimail,
        "console.api.users.delete": _console_api_delete_users,
        "console.api.users.reset_password": _console_api_reset_password,
        "console.api.renew_login": _console_api_renew_login,
        "console.all": {_console_index: ('GET', '/console/?'), _console_users: ('GET', '/console/users/?'), _console_change_or_create_user: ('GET', '/console/changeorcreateuser'), _console_summary_users: ('GET', '/console/api/summary.users'), _console_api_get_user: ('GET', '/console/api/user/get'), _console_api_change_or_create_user: ('PUT', '/console/api/changeorcreateuser'), _console_api_verify_users: ('POST', '/console/api/users/verify'), _console_api_deverify_users: ('POST', '/console/api/users/deverify'), _console_api_verimail: ('POST', '/console/api/users/verimail'), _console_api_delete_users: ('DELETE', '/console/api/users/delete'), _console_api_reset_password: ('DELETE', '/console/api/users/resetpassword'), _console_api_renew_login: ('POST', '/console/api/renewlogin')}
    }
    if not function.lower() in supported_funcs.keys():
        raise ValueError(
            f"function '{function.lower()}' not supported. Supported are " + "\n- " + "\n- ".join(supported_funcs.keys()))
    func = supported_funcs[function.lower()]
    if type(func) == dict:
        for f, endpoint in func.items():
            serverly._sitemap.register_site(endpoint[0], f, endpoint[1])
            _reversed_api[f.__name__] = endpoint[1]
    else:
        serverly._sitemap.register_site(method, func, path)
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


def _get_content(base: str, **extra_subs):
    return string.Template(base).safe_substitute(**_reversed_api, **extra_subs)


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


def _serve_console_static_files(func):
    required_files = {
        "^/console/static/css/main.css$": serverly.default_sites.console_css_main,
        "^/console/static/js/main.js$": serverly.default_sites.console_js_main
    }
    for path in required_files.keys():
        os.makedirs("/".join(path[2:-1].split("/")[:-1]), exist_ok=True)
    for path, content in required_files.items():
        if serverly._sitemap.methods["get"].get(path, "no") == "no":
            fpath = path[2:-1]
            with open(fpath, "w+") as f:
                f.write(content)
            serverly.static_page(fpath, path)

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@_serve_console_static_files
def _console_index(request: Request):
    def regular():
        content = _get_content(serverly.default_sites.console_index)
        return Response(body=content)

    admin = False
    users = serverly.user.get_all()
    for u in users:
        if u.role == "admin":
            admin = True

    if admin:
        res = _console_api_renew_login(request)
        if res.code == 200:
            return regular()
        else:
            return res
    else:
        password = serverly.utils.ranstr()
        serverly.user.register("root", password, role="admin")
        serverly.user.mail.manager.schedule(
            {"email": serverly.user.mail.manager.email_address, "subject": "serverly admin user", "content": f"Hey there,\nit seemed like you didn't have any admins left, so we registered a new root user for you. The password is: <b>{password}</b>. Make sure to delete it when you registered a new admin account for yourself.\n\nHave a great day!", "substitute": False})
        return Response(body=f"<html><head><meta charset='UFT-8'/></head><body><p>Created root user. Password: {password}</p></body></html>")


@_serve_console_static_files
@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_users(request: Request):
    user_table = "<table id='users'><thead><tr><th><input type='checkbox' id='select-master'></input></th>"
    users = serverly.utils.clean_user_object(serverly.user.get_all(), "id")
    for attribute in users[0].keys():
        user_table += "<th>" + str(attribute) + "</th>"
    user_table += "</tr></thead><tbody>"
    for user in users:
        user_table += f"<tr><td><input type='checkbox' class='user-select' id='user-{user['id']}'></input></td>"
        for attribute, value in user.items():
            user_table += "<td>" + str(value) + "</td>"
        user_table += "</tr>"
    user_table += "</tbody></table>"
    content = _get_content(
        serverly.default_sites.console_users, user_table=user_table)
    return Response(body=content)


@_serve_console_static_files
@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_change_or_create_user(request: Request):
    try:
        ids = parse.parse_qs(request.path.query).get(
            "ids", "")[0].split(",")
        if ids[-1] == "":
            ids.pop()
        ids = [int(i) for i in ids]
        content = _get_content(
            serverly.default_sites.console_user_change_or_create, user_ids=json.dumps(ids))
        return Response(body=content)
    except IndexError:
        path = "SUPERPATH" + _reversed_api["_console_users"]
        return Redirect(path)
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_summary_users(request: Request):
    try:
        users = serverly.user.get_all()

        n_users = len(users)
        n_emails = 0
        n_verified = 0

        for user in users:
            n_emails += 1 if user.email != None else 0
            n_verified += 1 if user.verified else 0

        return Response(body=f"There are {n_users} users with {n_emails} emails, {n_verified} of which are verified.")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_change_or_create_user(request: Request):
    try:
        def create():
            attrs = {}
            for k, v in request.obj.items():
                if k != "username" and k != "newPassword":
                    attrs[k] = v
            serverly.user.register(
                request.obj["username"], request.obj["newPassword"], **attrs)
            return Response(201, body="Registered user.")

        def change():
            username = request.obj.get("username", None)
            password = request.obj.get("newPassword", None)
            del request.obj["username"]
            del request.obj["newPassword"]
            serverly.user.change(user.username, username,
                                 password, **request.obj)
            return Response(body="Changed user.")

        id_ = request.obj.get("id", None)
        if id_ == None:
            return create()
        user = serverly.user.get_by_id(id_, False)
        if user:
            return change()
        else:
            return create()
    except (KeyError, ValueError) as e:
        serverly.logger.handle_exception(e)
        return _RES_406
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_get_user(request: Request):
    try:
        q = parse.parse_qs(request.path.query)
        i = int(q["id"][0])
        u = serverly.user.get_by_id(i)
        return Response(body=serverly.utils.clean_user_object(u, "password", "id"))
    except serverly.user.err.UserNotFoundError:
        return Response(404, body="User not found.")
    except (KeyError, TypeError) as e:
        serverly.logger.handle_exception(e)
        return Response(406, body="Expected id parameter.")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_verify_users(request: Request):
    try:
        c = 0
        for id_ in request.obj:
            try:
                user = serverly.user.get_by_id(id_)
                if not user.verified:
                    serverly.user.change(user.username, verified=True)
                    c += 1
            except:
                pass
        return Response(body=f"Verified emails of {c} users!")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_deverify_users(request: Request):
    try:
        c = 0
        for id_ in request.obj:
            try:
                user = serverly.user.get_by_id(id_)
                if user.verified:
                    serverly.user.change(user.username, verified=False)
                    c += 1
            except:
                pass
        return Response(body=f"Deverified emails of {c} users!")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_verimail(request: Request):
    try:
        c = 0
        for id_ in request.obj:
            try:
                user = serverly.user.get_by_id(id_)
                serverly.user.mail.manager.schedule_confirmation_mail(
                    user.username)
                c += 1
            except:
                pass
        return Response(body=f"Scheduled {c} verification mails!")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_delete_users(request: Request):
    try:
        c = 0
        for id_ in request.obj:
            try:
                user = serverly.user.get_by_id(id_)
                serverly.user.delete(user.username)
                c += 1
            except:
                pass
        return Response(body=f"Deleted {c} users!")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


def _console_api_renew_login(request: Request):
    try:
        assert request.auth_type.lower() == "basic"
        user = serverly.user.get(request.user_cred[0])
        assert user.role == "admin"
        serverly.user.authenticate(user.username, request.user_cred[1], True)
        return Response()
    except (AssertionError, serverly.user.err.UserNotFoundError, AttributeError, TypeError, serverly.user.err.NotAuthorizedError):
        return Response(401, {"WWW-Authenticate": "Basic"})
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(500, body=str(e))


@basic_auth
@_check_to_use_sessions
@requires_role("admin")
def _console_api_reset_password(request: Request):
    try:
        c = 0
        for id_ in request.obj:
            try:
                user = serverly.user.get_by_id(id_)
                serverly.user.mail.manager.schedule_password_reset_mail(
                    user.username)
                c += 1
            except:
                pass
        return Response(body=f"Scheduled {c} password reset emails.")
    except Exception as e:
        serverly.logger.handle_exception(e)
        return Response(body=str(e))
