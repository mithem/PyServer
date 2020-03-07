import re
import warnings
import importlib
import urllib.parse as parse
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer
from serverly.utils import *

from fileloghelper import Logger

version = "0.0.8"
description = "A really simple-to-use HTTP-server"
address = ("localhost", 8080)
name = "PyServer"
logger = Logger("serverly.log", "serverly", False, False)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.set_context(name + ": GET")
        parsed_url = parse.urlparse(self.path)
        response_code, content, info = _sitemap.get_content(
            "GET", parsed_url.path)
        logger.debug(
            f"\nresponse_code: {response_code}\ninfo: {info}\ncontent: {content}")
        self.send_response(response_code)
        for key, value in info.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(bytes(content, "utf-8"))

    def do_POST(self):
        logger.set_context(name + ": POST")
        parsed_url = parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = str(self.rfile.read(length), "utf-8")
        response_code, content, info = _sitemap.get_content(
            "POST", parsed_url.path, data)
        logger.debug(
            f"POST\ncode: {response_code}\ninfo: {info}\ncontent: {content}")
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

    @classmethod
    def _get_server_address(cls, address):
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
            logger.success(f"Server started http://{address[0]}:{address[1]}")
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
        if self.path == "^error$" or self.path == "none" or self.file_path == "^error$" or self.file_path == "none":
            content = "<html><head><title>Error</title></head><body><h1>An error occured.</h1></body></html>"
        else:
            with open(self.file_path, "r") as f:
                content = f.read()
        return content


class Sitemap:
    def __init__(self, superpath: str = "/", error_page=None):
        check_relative_path(superpath)
        self.superpath = superpath
        self.methods = {
            "get": {},
            "post": {}
        }
        if error_page == None:
            self.error_page = StaticSite("error", "none")
        elif issubclass(error_page.__class__, StaticSite):
            self.error_page = error_page
        else:
            raise Exception(
                "error_page argument expected to a be of subclass 'Site'")

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
            site = self.error_page
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
        return response_code, text, info


_sitemap = Sitemap()


def serves_get(path):
    """when using this wrapper, please return a tuple with a dict containing 'response_code', and the content as a str.

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


def serves_post(path):
    """when using this wrapper, please return a tuple with a dict containing 'response_code', and the content as a str.

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
    check_relative_file_path(file_path)
    check_relative_path(path)
    site = StaticSite(path, file_path)
    _sitemap.register_site("GET", site)


def start(superpath="/"):
    logger.autosave = True
    logger.header(True, True, description, version=True)
    _sitemap.superpath = superpath
    _server = Server(address)
    _server.run()
