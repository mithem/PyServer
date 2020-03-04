import re
import warnings
import importlib
import urllib.parse as parse
from functools import wraps
from http.server import BaseHTTPRequestHandler, HTTPServer
from PyServer.utils import *

from fileloghelper import Logger

address = ("localhost", 8080)
logger = Logger()
_static_sites = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = parse.urlparse(self.path)
        content = _sitemap.get_content("GET", parsed_url.path)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", len(content))
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
        self._logger = Logger(self.name + ".log", "pyserver", True, True)
        self.server_address = self._get_server_address(server_address)
        self.webaddress = webaddress
        self.cleanup_function = None
        self._handler: BaseHTTPRequestHandler = Handler
        self._server: HTTPServer = HTTPServer(
            self.server_address, self._handler)
        self._logger.header(True, True, description)
        self._logger.success(self.name + " initialized.", False)

    @classmethod
    def _get_server_address(cls, address):
        """returns tupe[str, int], e.g. ('localhost', 8080)"""
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
            self._server.serve_forever()
        except KeyboardInterrupt:
            self._server.server_close()
            if callable(self.cleanup_function):
                self.cleanup_function()


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
        if self.path == "^error$" or self.path == "none" or self.file_path == "^error$" or self.file_path == "none":
            return "<html><head><title>Error</title></head><body><h1>An error occured.</h1></body></html>"
        with open(self.file_path, "r") as f:
            return f.read()


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
        method = get_http_method_type(method)
        if issubclass(site.__class__, StaticSite):
            self.methods[method][site.path] = site
        elif callable(site):
            check_relative_path(path)
            if path[0] != "^":
                path = "^" + path
            if path[-1] != "$":
                path = path + "$"
            self.methods[method][path] = site
        else:
            raise TypeError("site argument not a subclass of 'Site'.")

    def get_content(self, method: str, path: str):
        method = get_http_method_type(method)
        check_relative_path(path)
        site = None
        for pattern in self.methods[method]:
            if re.match(pattern, path):
                site = self.methods[method][pattern]
        if site == None:
            site = self.error_page
        if isinstance(site, StaticSite):
            content = site.get_content()
        elif callable(site):
            content = site()
        return content


_sitemap = Sitemap()


def serves_get(path):
    def my_wrap(func):
        _sitemap.register_site("GET", func, path)
        logger.debug("registered function: " + func.__name__, True)
        @wraps(func)
        def wrapper(*args, **kwargs):
            print("function '" + func.__name__ +
                  "' serves path '" + path + "'.")
            return func(*args, **kwargs)
        return wrapper
    return my_wrap


def static_page(file_path, path):
    check_relative_file_path(file_path)
    check_relative_path(path)
    _static_sites.append(StaticSite(path, file_path))


def start():
    for f in _static_sites:
        _sitemap.register_site("GET", f)

    _server = Server(address)
    _server.run()
