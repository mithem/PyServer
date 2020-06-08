"""
serverly - http.server wrapper and helper
--


Attributes
--
`address: tuple = ('localhost', 8080)` The address used to register the server. Needs to be set before running start()

`name: str = 'PyServer'` The name of the server. Used for logging purposes only.

`logger: fileloghelper.Logger = Logger()` The logger used for logging (surprise!!). See the docs of fileloghelper for reference.


Methods
--
`static_page(file_path, path)` register a static page while the file is located under `file_path` and will serve `path`

`register(func, path: str)`

`unregister(method: str, path: str)`unregister any page (static or dynamic). Only affect the `method`-path (GET / POST)

`start(superpath: str="/")` start the server after applying all relevant attributes like address. `superpath` will replace every occurence of SUPERPATH/ or /SUPERPATH/ with `superpath`. Especially useful for servers orchestrating other servers.


Decorators (technically methods)
--
`serves(method: str, path: str)` Register the function to serve a specific path.
Example:
```
@serves_get("/hello(world)?")
def hello_world(data):
    return {"response_code": 200, "c": "text/plain"}, "Hello world!"
```
This will return "Hello World!" with a status code of 200, as plain text to the client
"""


import importlib
import multiprocessing
import re
import time
import urllib.parse as parse
import warnings
from functools import wraps
from typing import Union

import serverly.stater
import serverly.statistics
import uvicorn
from fileloghelper import Logger
from serverly import default_sites
from serverly.objects import Request, Response, StaticSite
from serverly.utils import *

description = "A really simple-to-use HTTP-server"
address = ("localhost", 8080)
name = "serverly"
version = "0.4.4"
logger = Logger("serverly.log", "serverly", False, True)
logger.header(True, True, description, fileloghelper_version=True,
              program_version="serverly v" + version)
error_response_templates = {}


async def _read_body(receive):
    """
    Read and return the entire body from an incoming ASGI message.
    http://www.uvicorn.org/#http-scope
    """
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return body.decode("utf-8")


async def _uvicorn_server(scope, receive, send):
    t1 = time.perf_counter()
    func = "some_error"
    if scope["type"].startswith("lifespan"):
        event = await receive()
        s = event["type"].replace("lifespan.", "")
        _update_status(s)
    elif scope["type"] == "http":
        try:
            b = await _read_body(receive)
            full_url = scope["path"] + "?" + \
                str(scope["query_string"], "utf-8")
            headers = {}
            for hl in scope["headers"]:
                if hl[0] != "authorization":
                    v = str(hl[1], "utf-8")
                else:
                    v = hl[1]
                headers[str(hl[0], "utf-8")] = v
            request = Request(scope["method"], parse.urlparse(full_url),
                              headers, b, scope["client"])
            func, response = _sitemap.get_content(request)
            response_headers = []
            for k, v in response.headers.items():
                response_headers.append(
                    [bytes(k, "utf-8"), serverly.utils.get_bytes(v)])
            t2 = time.perf_counter()
            await send({
                "type": "http.response.start",
                "status": response.code,
                "headers": response_headers
            })
            mimetype = response.headers.get("content-type", None)
            if response.bandwidth == None:
                await send({
                    "type": "http.response.body",
                    "body": serverly.utils.get_bytes(response.body, mimetype)
                })
            else:
                chunks = serverly.utils.get_chunked_response(response)
                need_to_regulate = len(chunks) > 1
                for chunk in chunks[:-1]:
                    await send({"type": "http.response.body",
                                "body": serverly.utils.get_bytes(chunk, mimetype),
                                "more_body": True
                                })
                    if need_to_regulate:
                        time.sleep(1)
                await send({
                    "type": "http.response.body",
                    "body": serverly.utils.get_bytes(chunks[-1], mimetype)
                })
        except Exception as e:
            logger.handle_exception(e)
            if scope["type"] != "lifespan":
                c = bytes(
                    "Sorry, but serverly made a mistake sending the response. Please inform the administrator.", "utf-8")
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [[b"content-type", b"text/html"], [b"content-length", bytes(str(len(c)), "utf-8")]]
                })
                await send({
                    "type": "http.response.body",
                    "body": c
                })
        serverly.statistics.new_statistic(func, t2 - t1)

    else:
        try:
            raise NotImplementedError(
                f"Unsupported ASGI type '{scope['type']}'.")
        except Exception as e:
            logger.context = "client connection"
            logger.show_warning(e)


class Server:
    def __init__(self, server_address, name="serverly", description="A serverly instance."):
        self.name = name
        self.description = description
        self.server_address = get_server_address(server_address)
        self.cleanup_function = None
        logger.context = "startup"
        logger.success("Server initialized", False)

    def run(self, ssl_key_file: str = None, ssl_cert_file: str = None, redirect_to_https=True):
        try:
            serverly.stater.set(0)
        except Exception as e:
            logger.handle_exception(e)
        log_level = "info" if _sitemap.debug else "warning"
        self.ssl_key_file = ssl_key_file
        self.ssl_cert_file = ssl_cert_file
        self.redirect_to_https = redirect_to_https
        kwargs = {}
        if ssl_key_file != None:
            kwargs["ssl_keyfile"] = ssl_key_file
        if ssl_cert_file != None:
            kwargs["ssl_certfile"] = ssl_cert_file
        uvicorn.run(_uvicorn_server,
                    host=address[0], port=address[1], log_level=log_level, lifespan="on", **kwargs)
        self.close()

    def close(self):
        logger.context = "shutdown"
        logger.debug("Shutting down server…", True)
        try:
            serverly.stater.set(3)
        except Exception as e:
            logger.handle_exception(e)
        if callable(self.cleanup_function):
            self.cleanup_function()
        logger.success("Server stopped.")
        serverly.statistics.print_stats()
        exit(0)


_server: Server = None


def _update_status(new_status: str):
    """[internal] Update status of the server and act/log accordingly. Accepts status str as specified a ASGI lifespan."""
    if new_status == "startup":
        logger.context = "startup"
        prefix = "https" if _server.ssl_cert_file != None and _server.ssl_key_file != None else "http"
        logger.success(
            f"Server started {prefix}://{address[0]}:{address[1]} with superpath '{_sitemap.superpath}'")
    elif new_status == "startup.failed" or new_status == "shutdown":
        _server.close()
    else:
        logger.warning(Exception(
            f"_update_status() was called with an invalid parameter 'new_status' of '{new_status}' (type {type(new_status)})"))


def _verify_user(req: Request):
    identifier = req.path.path.split("/")[-1]
    import serverly.user.mail
    r = serverly.user.mail.verify(identifier)
    if r:
        return Response(body="<html><head><meta charset='utf-8'/></head><pre>You're verified 🎉</pre></html>")
    else:
        return Response(body="<html><p>Either the verification code is invalid or you already are verified.</p></html>")


def _confirm_user(req: Request):
    identifier = req.path.path.split("/")[-1]
    import serverly.user.mail
    r = serverly.user.mail.confirm(identifier)
    if r:
        return Response(body="<html><head><meta charset='utf-8'/></head><pre>You're verified 🎉</pre></html>")
    else:
        return Response(body="<html><p>Either the verification code is invalid or you already are verified.</p></html>")


def _reset_password_user_endpoint(req: Request):
    identifier = req.path.path.split("/")[2]
    return Response(body=string.Template(serverly.default_sites.password_reset_page).safe_substitute(identifier=identifier))


def _reset_password_for_real(req: Request):
    try:
        if req.auth_type.lower() == "bearer":
            identifier = req.user_cred
            import serverly.user.mail
            r = serverly.user.mail.reset_password(
                identifier, req.obj["password"])
            if r:
                return Response(body="Changed password successfully!")
            else:
                return Response(body="Either the identifier is invalid or you already reset your password via this token.")
        return Response(401, {"WWW-Authenticate": "Bearer"}, "Invalid authentication")
    except Exception as e:
        return Response(500, body=str(e))


class Sitemap:
    def __init__(self, superpath: str = "/", error_page: dict = None, debug=False):
        """[internal]

        :param superpath: path which will replace every occurence of '/SUPERPATH/' or 'SUPERPATH/'. Great for accessing multiple servers from one domain and forwarding the requests to this server.
        :param error_page: default error page

        :type superpath: str
        :type error_page: StaticPage
        """
        check_relative_path(superpath)
        self.superpath = superpath
        self.debug = debug
        self.methods = {
            "get": {r"^/verify/[\w0-9]+$": _verify_user, r"^/reset-password/[\w0-9]+$": _reset_password_user_endpoint, r"^/confirm/[\w0-9]+$": _confirm_user},
            "post": {"^/api/resetpassword/?$": _reset_password_for_real},
            "put": {},
            "delete": {}
        }

    def register_site(self, method: str, site: StaticSite, path=None):
        logger.context = "registration"
        method = get_http_method_type(method)
        if issubclass(site.__class__, StaticSite):
            p = site.path if not path else path
            self.methods[method][p] = site
            logger.success(
                f"Registered {method.upper()} static site for path '{site.path}'.", False)
        elif callable(site):
            check_relative_path(path)
            if path[0] != "^":
                path = "^" + path
            if path[-1] != "$":
                path = path + "$"
            self.methods[method][path] = site
            logger.success(
                f"Registered {method.upper()} function '{site.__name__}' for path '{path}'.", False)
        else:
            raise TypeError("site argument not a subclass of 'Site'.")

    def unregister_site(self, method: str, path: str):
        method = get_http_method_type(method)
        check_relative_path(path)
        if path[0] != "^":
            path = "^" + path
        if path[-1] != "$":
            path = path + "$"
        found = False
        for key in self.methods[method].keys():
            if path == key:
                found = True
        logger.context = "registration"
        if found:
            del self.methods[method][key]
            logger.debug(
                f"Unregistered site/function for path '{path}'")
            return True
        else:
            logger.warning(
                f"Site for path '{path}' not found. Cannot be unregistered.")
            return False

    def get_func_or_site_response(self, site, request: Request):
        try:
            s = "unknown"
            response = Response()
            if isinstance(site, StaticSite):
                response = site.get_content()
                s = str(site)
            else:
                s = site.__name__
                try:
                    content = site(request)
                except TypeError as e:  # makes debugging easier
                    serverly.logger.handle_exception(e)
                    try:
                        content = site()
                    except TypeError as e:
                        logger.handle_exception(e)
                        raise TypeError(
                            f"Function '{site.__name__}' either takes to many arguments (only object of type Request provided) or raises a TypeError")
                except Exception as e:
                    serverly.logger.debug("Site: " + site.__name__, self.debug)
                    logger.handle_exception(e)
                    response = error_response(500)
                if isinstance(content, Response):
                    response = content
                else:
                    try:
                        raise UserWarning(
                            f"Function for '{request.path.path}' ({site.__name__}) needs to return a Response object. Website will be a warning message (not your content but serverly's).")
                    except Exception as e:
                        logger.handle_exception(e)
                    response = error_response(942)
            headers = response.headers
            for k, v in headers.items():
                try:
                    headers[k] = v.replace(
                        "/SUPERPATH/", self.superpath).replace("SUPERPATH/", self.superpath)
                except:
                    pass
            response.headers = headers
            try:
                response.body = response.body.replace(
                    "/SUPERPATH/", self.superpath).replace("SUPERPATH/", self.superpath)
            except:
                pass
            return (s, response)
        except Exception as e:
            logger.handle_exception(e)
            return error_response(500, str(e))

    def get_content(self, request: Request):
        site = None
        response = None
        func = "unknown_error"
        for pattern in self.methods[request.method].keys():
            if re.match(pattern, request.path.path):
                site = self.methods[request.method][pattern]
                break
        if site == None:
            response = error_response(404)
            return (func, response)
        try:
            func, response = self.get_func_or_site_response(
                site, request)
        except Exception as e:
            logger.handle_exception(e)
            site = error_response(500)
            response = self.get_func_or_site_response(
                site, "")
            serverly.stater.error(logger)
        return (func, response)


_sitemap = Sitemap()


def serves(method: str, path: str):
    """Decorator for registering a function for `path`, with `method`"""
    def wrapper_function(func):
        _sitemap.register_site(method, func, path)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return wrapper_function


def static_page(file_path: str, path: str):
    """Register a static page where the file is located under `file_path` and will serve `path`"""
    check_relative_file_path(file_path)
    check_relative_path(path)
    site = StaticSite(path, file_path)
    _sitemap.register_site("GET", site)


def register_function(method: str, path: str, function):
    if callable(function):
        _sitemap.register_site(method, function, path)
    else:
        raise TypeError("'function' not callable.")


def unregister(method: str, path: str):
    """Unregister any page (static or dynamic). Return bool whether successful (found page)."""
    return _sitemap.unregister_site(method, path)


def _start_server(superpath: str, debug=False, ssl_key_file: str = None, ssl_cert_file: str = None, redirect_to_https=True):
    global _sitemap, _server
    _sitemap.superpath = superpath
    _sitemap.debug = debug
    _server = Server(address)
    _server.run(ssl_key_file, ssl_cert_file, redirect_to_https)


def start(superpath: str = '/', mail_active=False, debug=False, ssl_key_file: str = None, ssl_cert_file: str = None, redirect_to_https=True):
    """Start the server after applying all relevant attributes like address. `superpath` will replace every occurence of SUPERPATH/ or /SUPERPATH/ with `superpath`. Especially useful for servers orchestrating other servers."""
    try:
        logger.verbose = debug
        args = tuple([superpath, debug, ssl_key_file,
                      ssl_cert_file, redirect_to_https])
        server = multiprocessing.Process(
            target=_start_server, args=args)
        if mail_active:
            import serverly.user.mail
            mail_manager = multiprocessing.Process(
                target=serverly.user.mail.manager.start)
            mail_manager.start()
        server.start()
    except KeyboardInterrupt:
        try:
            del _server
            server.join()
            mail_manager.join()
        except Exception as e:
            logger.handle_exception(e)


def register_error_response(code: int, msg_base: str, mode="enumerate"):
    """register an error response template for `code` based off the message-stem `msg_base`and accepting *args as defined by `mode`

    Modes
    ---
    - enumerate: append every arg by comma and space to the base
    - base: only return the base message

    Example
    ---
    ```
    register_error_response(404, 'Page not found.', 'base'
    ```
    You can now get the 404-Response by calling `error_response(404)` -> Response(code=404, body='Page not found.')
    Or in enumerate mode:
    ```
    register_error_response(999, 'I want to buy: ', 'enumerate')
    ```
    `error_response(999, 'apples', 'pineapples', 'bananas')` -> Response(code=9l9, body='I want to buy: apples, pineapples, bananas')
    """
    def enumer(msg_base, *args):
        result = msg_base + ', '.join(args)
        if result[-1] != ".":
            result += "."
        return result

    def base_only(msg_base, *args):
        if msg_base[-1] != ".":
            msg_base += "."
        return msg_base

    if mode.lower() == "enumerate" or mode.lower() == "enum":
        error_response_templates[code] = (enumer, msg_base)
    elif mode.lower() == "base":
        error_response_templates[code] = (base_only, msg_base)
    else:
        raise ValueError("Mode not valid. Expected 'enumerate' or 'base'.")


def error_response(code: int, *args):
    """Define template error responses by calling serverly.register_error_response(code: int, msg_base: str, mode="enumerate")"""
    try:
        t = error_response_templates[code]
        return Response(code, body=t[0](t[1], *args))
    except KeyError:
        raise ValueError(
            f"No template found for code {str(code)}. Please make sure to register them by calling register_error_response.")
    except Exception as e:
        logger.handle_exception(e)


register_error_response(
    500, "500 - Internal server error - Sorry, something went wrong on our side.", "base")
register_error_response(404, "<html><p>404 - Page not found</p></html>")
register_error_response(
    942, "<html><h3>502 - Bad Gateway.</h3><br />Sorry, there is an error with the function serving this site. Please advise the server administrator that the function for '{req.path.path}' is not returning a response object.</html>", "base")
