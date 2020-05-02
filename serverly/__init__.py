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
    return {"response_code": 200, "Content-type": "text/plain"}, "Hello world!"
```
This will return "Hello World!" with a status code of 200, as plain text to the client
"""
import importlib
import mimetypes
import multiprocessing
import re
import time
import urllib.parse as parse
import warnings
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Union

import serverly.stater
import serverly.statistics
from fileloghelper import Logger
from serverly import default_sites
from serverly.objects import Request, Response
from serverly.utils import *

description = "A really simple-to-use HTTP-server"
address = ("localhost", 8080)
name = "serverly"
version = "0.4.0"
logger = Logger("serverly.log", "serverly", False, False)
logger.header(True, True, description, fileloghelper_version=True,
              program_version="serverly v" + version)
error_response_templates = {}


class Handler(BaseHTTPRequestHandler):

    def respond(self, response: Response):
        self.send_response(response.code)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(bytes(response.body, "utf-8"))

    def handle_request(self, method: str):
        try:
            parsed_url = parse.urlparse(self.path)
            data_length = int(self.headers.get("Content-Length", 0))
            received_data = str(self.rfile.read(data_length), "utf-8")
            request = Request(method, parsed_url, dict(
                self.headers), received_data, self.client_address)
            t1 = time.perf_counter()
            response = _sitemap.get_content(request)
            t2 = time.perf_counter()
            self.respond(response)
            logger.context = name + ": " + method
            logger.debug(str(response))
            serverly.statistics.calculation_times.append(t2 - t1)
        except Exception as e:
            serverly.stater.error(logger)
            logger.handle_exception(e)
            raise e

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")

    def do_PUT(self):
        self.handle_request("PUT")

    def do_DELETE(self):
        self.handle_request("DELETE")


class Server:
    def __init__(self, server_address, webaddress="/", name="serverly", description="A serverly instance."):
        """
        :param webaddress: the internet address this server is accessed by (optional). It will automatically be inserted where a URL is recognized to be one of this server.
        :type webaddress: str
        """
        self.name = name
        self.description = description
        self.server_address = self._get_server_address(server_address)
        self.webaddress = webaddress
        self.cleanup_function = None
        self._handler: BaseHTTPRequestHandler = Handler
        self._server: HTTPServer = HTTPServer(
            self.server_address, self._handler)
        logger.context = "startup"
        logger.success("Server initialized", False)

    @staticmethod
    def _get_server_address(address):
        """returns tupe[str, int], e.g. ('localhost', 8080)"""
        hostname = ""
        port = 0

        def valid_hostname(name):
            return bool(re.match(r"^[_a-zA-Z.-]+$", name))
        if type(address) == str:
            pattern = r"^(?P<hostname>[_a-zA-Z.-]+)((,|, |;|; )(?P<port>[0-9]{2,6}))?$"
            match = re.match(pattern, address)
            hostname, port = match.group("hostname"), int(match.group("port"))
        elif type(address) == tuple:
            if type(address[0]) == str:
                if valid_hostname(address[0]):
                    hostname = address[0]
            if type(address[1]) == int:
                if address[1] > 0:
                    port = address[1]
            elif type(address[0]) == int and type(address[1]) == str:
                if valid_hostname(address[1]):
                    hostname = address[1]
                    if address[0] > 0:
                        port = address[0]
                else:
                    warnings.warn(UserWarning(
                        "hostname and port are in the wrong order. Ideally, the addresses is a tuple[str, int]."))
                    raise Exception("hostname specified not valid")
        else:
            raise TypeError(
                "address argument not of valid type. Expected type[str, int] (hostname, port)")

        return (hostname, port)

    def run(self):
        try:
            try:
                serverly.stater.set(0)
            except Exception as e:
                logger.handle_exception(e)
            logger.context = "startup"
            logger.success(
                f"Server started http://{address[0]}:{address[1]} with superpath '{_sitemap.superpath}'")
            self._server.serve_forever()
        except KeyboardInterrupt:
            logger.context = "shutdown"
            logger.debug("Shutting down server…", True)
            try:
                serverly.stater.set(3)
            except Exception as e:
                logger.handle_exception(e)
            self._server.shutdown()
            self._server.server_close()
            if callable(self.cleanup_function):
                self.cleanup_function()
            logger.success("Server stopped.")
            serverly.statistics.print_stats()


_server: Server = None


class StaticSite:
    def __init__(self, path: str, file_path: str):
        check_relative_path(path)
        self.file_path = check_relative_file_path(file_path)
        if path[0] != "^":
            path = "^" + path
        if path[-1] != "$":
            path = path + "$"
        self.path = path

    def get_content(self):
        content = ""
        if self.path == "^/error$" or self.path == "none" or self.file_path == "^/error$" or self.file_path == "none":
            content = "<html><head><title>Error</title></head><body><h1>An error occured.</h1></body></html>"
        else:
            with open(self.file_path, "r") as f:
                content = f.read()
        return content


def _verify_user(req: Request):
    try:
        identifier = req.path.path.split("/")[-1]
        import serverly.user.mail
        serverly.user.mail.verify(identifier)
        return Response(body="You're verified 🎉")
    except KeyError:
        return Response(404, body="Sorry, but the verification code seems to be invalid.")


class Sitemap:
    def __init__(self, superpath: str = "/", error_page: dict = None):
        """
        Create a new Sitemap instance
        :param superpath: path which will replace every occurence of '/SUPERPATH/' or 'SUPERPATH/'. Great for accessing multiple servers from one domain and forwarding the requests to this server.
        :param error_page: default error page

        :type superpath: str
        :type error_page: StaticPage
        """
        check_relative_path(superpath)
        self.superpath = superpath
        self.methods = {
            # for verifying users of serverly.user and serverly.user.mail
            "get": {"^/verify/[\w0-9]+": _verify_user},
            "post": {},
            "put": {},
            "delete": {}
        }
        if error_page == None:
            self.error_page = {
                0: StaticSite(
                    "/error", "none"),
                404: default_sites.page_not_found_error,
                500: default_sites.general_server_error,
                942: default_sites.user_function_did_not_return_response_object
            }
        elif issubclass(error_page.__class__, StaticSite):
            self.error_page = {0: error_page}
        elif type(error_page) == dict:
            for key, value in error_page.items():
                if type(key) != int:
                    raise TypeError(
                        "error_page: dict keys not of type int (are used as response_codes)")
                if not issubclass(error_page.__class__, StaticSite) and not callable(error_page):
                    raise TypeError(
                        "error_page is neither a StaticSite nor a function.")
        else:
            raise Exception(
                "error_page argument expected to of type dict[int, Site], or a subclass of 'StaticSite'")

    def register_site(self, method: str, site: StaticSite, path=None):
        logger.context = "registration"
        method = get_http_method_type(method)
        if issubclass(site.__class__, StaticSite):
            self.methods[method][site.path] = site
            logger.debug(
                f"Registered {method.upper()} static site for path '{site.path}'.")
        elif callable(site):
            check_relative_path(path)
            if path[0] != "^":
                path = "^" + path
            if path[-1] != "$":
                path = path + "$"
            self.methods[method][path] = site
            logger.debug(
                f"Registered {method.upper()} function '{site.__name__}' for path '{path}'.")
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
        if found:
            del self.methods[method][key]
            logger.context = "registration"
            logger.debug(
                f"Unregistered site/function for path '{path}'")
        else:
            logger.warning(
                f"Site for path '{path}' not found. Cannot be unregistered.")

    def get_func_or_site_response(self, site, request: Request):
        response = Response()
        if isinstance(site, StaticSite):
            response = Response(body=site.get_content())
        elif callable(site):
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
                    logger.handle_exception(e)
                    content = "500 - Internal server error - " + str(e)
                    raise e
            except Exception as e:
                logger.handle_exception(e)
                content = "500 - Internal server error - " + str(e)
                raise e
            response = Response(200, {}, "")
            if isinstance(content, Response):
                response = content
            else:
                try:
                    raise UserWarning(
                        f"Function for '{request.path}' needs to return a Response object. Website will be a warning message (not your content but serverly's).")
                except Exception as e:
                    logger.handle_exception(e)
                response = self.get_func_or_site_response(
                    self.error_page.get(942, self.error_page[0]), request)
        response.body = response.body.replace(
            "/SUPERPATH/", self.superpath).replace("SUPERPATH/", self.superpath)
        return response

    def get_content(self, request: Request):
        site = None
        response = None
        for pattern in self.methods[request.method].keys():
            if re.match(pattern, request.path.path):
                site = self.methods[request.method][pattern]
                break
        if site == None:
            site = self.error_page.get(404, self.error_page[0])
            response = self.get_func_or_site_response(
                site, request)
        try:
            response = self.get_func_or_site_response(
                site, request)
        except Exception as e:
            logger.handle_exception(e)
            site = self.error_page.get(500, self.error_page[0])
            response = self.get_func_or_site_response(
                site, "")
            serverly.stater.error(logger)
        return response


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
    """Unregister any page (static or dynamic). Only affect the `method`-path (GET / POST)"""
    check_relative_path(path)
    method = get_http_method_type(method)
    _sitemap.unregister_site(method, path)


def _start_server(superpath: str):
    _sitemap.superpath = superpath
    _server = Server(address)
    _server.run()


def start(superpath: str = '/', mail_active=False):
    """Start the server after applying all relevant attributes like address. `superpath` will replace every occurence of SUPERPATH/ or /SUPERPATH/ with `superpath`. Especially useful for servers orchestrating other servers."""
    try:
        logger.autosave = True
        args = tuple([superpath])
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
