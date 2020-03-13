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

`register_get(func, path: str)` register dynamic GET page (function)

`register_post(func, path: str)` register dynamic POST page (function)

`unregister(method: str, path: str)`unregister any page (static or dynamic). Only affect the `method`-path (GET / POST)

`start(superpath: str="/")` start the server after applying all relevant attributes like address. `superpath` will replace every occurence of SUPERPATH/ or /SUPERPATH/ with `superpath`. Especially useful for servers orchestrating other servers.


Decorators (technically methods)
--
`serves_get(path: str`/`serves_post(path: str)` Register the function to serve a specific path.
Example:
```
@serves_get("/hello(world)?")
def hello_world(data):
    return {"response_code": 200, "Content-type": "text/plain"}, "Hello world!"
```
This will return "Hello World!" with a status code of 200, as plain text to the client
"""
import importlib
import re
import urllib.parse as parse
import warnings
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer

from fileloghelper import Logger
from serverly import default_sites
from serverly.utils import *

version = "0.0.16"
description = "A really simple-to-use HTTP-server"
address = ("localhost", 8080)
name = "PyServer"
logger = Logger("serverly.log", "serverly", False, False)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = parse.urlparse(self.path)
        response_code, content, info = _sitemap.get_content(
            "GET", parsed_url.path)
        logger.set_context(name + ": GET")
        logger.debug(
            f"Sent {str(response_code)}, path {parsed_url.path} (GET)")
        print(response_code, info)
        self.send_response(response_code)
        for key in info:
            self.send_header(key, info[key])
            logger.debug(str(key) + "   " + str(info[key]))
        self.end_headers()
        self.wfile.write(bytes(content, "utf-8"))

    def do_POST(self):
        parsed_url = parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = str(self.rfile.read(length), "utf-8")
        response_code, content, info = _sitemap.get_content(
            "POST", parsed_url.path, data)
        logger.set_context(name + ": POST")
        logger.debug(
            f"Sent {str(response_code)}, path {parsed_url.path} (POST)")
        self.send_response(response_code)
        for key, value in info.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(bytes(content, "utf-8"))


class Server:
    def __init__(self, server_address, webaddress="/", name="pyserver", description="A PyServer instance."):
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
        logger.set_context("startup")
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
            logger.set_context("startup")
            logger.success(
                f"Server started http://{address[0]}:{address[1]} with superpath '{_sitemap.superpath}'")
            self._server.serve_forever()
        except KeyboardInterrupt:
            self._server.shutdown()
            self._server.server_close()
            if callable(self.cleanup_function):
                self.cleanup_function()
            logger.set_context("shutdown")
            logger.success("Server stopped.")


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
            "get": {},
            "post": {}
        }
        if error_page == None:
            self.error_page = {0: StaticSite(
                "/error", "none"), 404: default_sites.page_not_found_error, 500: default_sites.general_server_error}
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
        logger.set_context("registration")
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
                found = True  # deleting right here raises RuntimeError
        if found:
            del self.methods[method][key]
            logger.set_context("registration")
            logger.debug(
                f"Unregistered site/function for path '{path}'")
        else:
            logger.warning(
                f"Site for path '{path}' not found. Cannot be unregistered.")

    def get_func_or_site_response(self, site, received_data: str):
        response_code = 200
        if isinstance(site, StaticSite):
            text = site.get_content()
            info = {"Content-type": "text/html",
                    "Content-Length": len(text)}
        elif callable(site):
            type_error_msg = f"Stuff that was returned by function {site.__name__} is not acceptable. Expected tuple[dict, str]."
            try:
                content = site()
            except TypeError:
                try:
                    try:
                        data = json.loads(received_data)
                    except json.JSONDecodeError:
                        data = received_data
                    content = site(data)
                except TypeError as e:
                    logger.handle_exception(e)
                    raise TypeError(
                        f"Function '{site.__name__}' either takes to many arguments (only data: str provided) or raises a TypeError")
                except Exception as e:
                    logger.handle_exception(e)
            if type(content) == tuple:
                v1 = False
                v2 = False
                if type(content[0]) == str:
                    v1 = True
                    if type(content[1]) == dict:
                        response_code, info = parse_response_info(
                            content[1], len(content[0]))
                        text = content[0]
                        v2 = True
                    else:
                        raise TypeError(type_error_msg)
                if type(content[0]) == dict:
                    if type(content[1]) == str:
                        text = content[1]
                        v2 = True
                    else:
                        raise TypeError(type_error_msg)
                    response_code, info = parse_response_info(
                        content[0], len(content[1]))
                    v1 = True
                if not v1 and not v2:
                    raise ValueError(type_error_msg +
                                     " Response was: " + str(content))
            elif type(content) == str:
                response_code, info = guess_response_info(content)
                print(response_code, info)
                text = content
            elif type(content) == dict:
                info = content
                text = ""
        text = text.replace(
            "/SUPERPATH/", self.superpath).replace("SUPERPATH/", self.superpath)
        return response_code, info, text

    def get_content(self, method: str, path: str, received_data: str = ""):
        response_code = 500
        text = ""
        info = {}
        method = get_http_method_type(method)
        check_relative_path(path)
        site = None
        for pattern in self.methods[method]:
            if re.match(pattern, path):
                site = self.methods[method][pattern]
        if site == None:
            response_code = 404
            site = self.error_page.get(404, self.error_page[0])
        try:
            response_code, info, text = self.get_func_or_site_response(
                site, received_data)
        except Exception as e:
            logger.handle_exception(e)
            site = self.error_page.get(500, self.error_page[0])
            response_code, info, text = self.get_func_or_site_response(
                site, "")
            raise e
        return response_code, text, info


_sitemap = Sitemap()


def serves_get(path: str):
    """When using this wrapper, please return a tuple with a dict containing 'response_code', and the content as a str.

    Example(s): 

    return ({'response_code': 200}, 'Hello World!')

    You can also give more headers:

    return ({'response_code': 200, 'Content-type': 'text/plain', 'Content-Length': 4}, '1234')

    Or, if you'd like to type as little as you can:

    return {'code':200},'Hello there!'
    """
    def my_wrap(func):
        _sitemap.register_site("GET", func, path)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return my_wrap


def serves_post(path: str):
    """When using this wrapper, please return a tuple with a dict containing 'response_code', and the content as a str.

    Example(s): 

    return ({'response_code': 200}, 'Hello World!')

    You can also give more headers:

    return ({'response_code': 200, 'Content-type': 'text/plain', 'Content-Length': 4}, '1234')

    Or, if you'd like to type as little as you can:

    return {'code':200},'Hello there!'
    """
    def my_wrap(func):
        _sitemap.register_site("POST", func, path)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return my_wrap


def static_page(file_path, path):
    """Register a static page while the file is located under `file_path` and will serve `path`"""
    check_relative_file_path(file_path)
    check_relative_path(path)
    site = StaticSite(path, file_path)
    _sitemap.register_site("GET", site)


def register_get(func, path: str):
    """Register dynamic GET page (function)"""
    check_relative_path(path)
    if callable(func):
        _sitemap.register_site("GET", func, path)


def register_post(func, path: str):
    """Register dynamic POST page (function)"""
    check_relative_path(path)
    if callable(func):
        _sitemap.register_site("POST", func, path)


def unregister(method: str, path: str):
    """Unregister any page (static or dynamic). Only affect the `method`-path (GET / POST)"""
    check_relative_path(path)
    method = get_http_method_type(method)
    _sitemap.unregister_site(method, path)


def start(superpath: str = "/"):
    """Start the server after applying all relevant attributes like address. `superpath` will replace every occurence of SUPERPATH/ or /SUPERPATH/ with `superpath`. Especially useful for servers orchestrating other servers."""
    logger.autosave = True
    logger.header(True, True, description, fileloghelper_version=True,
                  program_version="serverly v" + version)
    _sitemap.superpath = superpath
    _server = Server(address)
    _server.run()
