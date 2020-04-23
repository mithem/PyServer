"""This module holds the serverly standard API. This allows you to just specify endpoints while serverly takes care of the actual API for registering users, etc.).

See the Postman documentation online: https://documenter.getpostman.com/view/10720102/Szf549XF?version=latest
"""
import serverly
import serverly.utils
from serverly import Request, Response, error_response
from serverly.user import err
import serverly.user

_RES_406 = Response(
    406, body="Unable to parse required parameters. Expected username, password.")
verify_mail = False
only_user_verified = False


def use(function: str, method: str, path: str, mail_verification=False, require_user_to_be_verified=False):
    """Serverly comes with builtin API-functions for the following serverly.user functions:
    - authenticate
    - change
    - delete
    - get
    - register
    - sessions.post (create new session or append to existing one)
    - sessions.get (get all sessions of user)
    - sessions.delete (delete all sessions of user)
    `function`accepts on of the above. The API-endpoint will be registered for `method`on `path`.

    Use `mail_verification` to control whether the register function should automatically try to verify the users' email. You can also manually do that by calling `serverly.user.mail.send_verification_email()`. If `require_user_to_be_verified`, users will only authenticate if their email is verified.
    """
    global verify_mail
    supported_funcs = {"authenticate": _api_authenticate, "change": _api_change,
                       "delete": _api_delete, "get": _api_get, "register": _api_register, "sessions.post": _api_sessions_post, "sessions.get": _api_sessions_get, "sessions.delete": _api_sessions_delete}
    if not function.lower() in supported_funcs.keys():
        raise ValueError(
            "function not supported. Supported are " + ", ".join(supported_funcs.keys()) + ".")
    serverly._sitemap.register_site(
        method, supported_funcs[function.lower()], path)

    if mail_verification:
        verify_mail = True
    if require_user_to_be_verified:
        only_user_verified = True


def _api_authenticate(req: Request):
    try:
        serverly.user.authenticate(req.user_cred[0], req.user_cred[1], True)
        response = Response()
    except TypeError:
        try:
            verified = True if only_user_verified else req.obj.get(
                "verified", only_user_verified)
            serverly.user.authenticate(
                req.obj["username"], req.obj["password"], True, verified)
            response = Response()
        except (AttributeError, KeyError, TypeError):
            response = _RES_406
        except err.UserNotFoundError as e:
            response = Response(404, body=str(e))
        except err.NotAuthorizedError:
            response = Response(401, body="Not authorized.")
        except Exception as e:
            serverly.logger.handle_exception(e)
            response = Response(500, body=str(e))
    # not merging these two caus a duplicate registration *needs* to tell that a certain username is already taken
    except err.UserNotFoundError as e:
        response = Response(404, body=str(e))
    except err.NotAuthorizedError:
        response = Response(401, body="Not authorized.")
    except Exception as e:
        response = Response(500, body=str(e))
    return response


def _api_change(req: Request):
    try:
        if not req.authenticated:
            raise err.MissingParameterError
        serverly.user.authenticate(req.user_cred[0], req.user_cred[1], True)
        serverly.user.change(req.user_cred[0], **req.obj)
        response = Response()
    except TypeError:
        response = Response(401, {"WWW-Authenticate": "Basic"})
    except err.UserNotFoundError as e:
        response = Response(404, body=str(e))
    except err.NotAuthorizedError:
        response = Response(401, body="Not authorized")
    except err.MissingParameterError:
        response = _RES_406
    return response


def _api_delete(req: Request):
    try:
        serverly.user.authenticate(req.user_cred[0], req.user_cred[1], True)
        serverly.user.delete(req.user_cred[0])
        response = Response()
    except TypeError:
        try:
            serverly.user.authenticate(
                req.obj["username"], req.obj["password"], True)
            serverly.user.delete(req.obj["username"])
            response = Response()
        except (TypeError, KeyError):
            response = _RES_406
    except err.UserNotFoundError as e:
        response = Response(404, body=str(e))
    except err.NotAuthorizedError:
        response = Response(401)
    except Exception as e:
        response = Response(500, body=str(e))
    return response


def _api_get(req: Request):
    try:
        serverly.user.authenticate(req.user_cred[0], req.user_cred[1], True)
        user = serverly.user.get(req.user_cred[0])
        response = Response(body=serverly.utils.clean_user_object(user))
    except TypeError:
        try:
            serverly.user.authenticate(
                req.obj["username"], req.obj["password"], True)
            user = serverly.user.get(req.obj["username"])
            response = Response(body=serverly.utils.clean_user_object(user))
        except (AttributeError, KeyError, TypeError) as e:
            response = _RES_406
    except err.UserNotFoundError as e:
        response = Response(404, body=str(e))
    except err.NotAuthorizedError:
        response = Response(401)
    except Exception as e:
        serverly.logger.handle_exception(e)
        response = Response(500, body=str(e))
    return response


def _api_register(req: Request):
    try:
        serverly.user.register(**req.obj)
        response = Response()
        if verify_mail:
            serverly.user.mail.manager.send_verification_mail(
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


@serverly.user.basic_auth
def _api_sessions_post(req: Request):
    serverly.user.new_activity(req.user.username, req.address)
    return Response()


@serverly.user.basic_auth
def _api_sessions_get(req: Request):
    ses = serverly.user.get_all_sessions(req.user.username)
    sessions = [s.to_dict()
                for s in ses]
    response = Response(body=sessions)
    return response


@serverly.user.basic_auth
def _api_sessions_delete(req: Request):
    serverly.user.delete_sessions(req.user.username)
    return Response()
