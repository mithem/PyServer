import base64
import collections.abc
import datetime
import json as jsonjson
import mimetypes
import os
import urllib.parse
import warnings
from typing import Union

from serverly.utils import (get_http_method_type, guess_response_headers,
                            is_json_serializable, check_relative_path, check_relative_file_path)


class DBObject:
    """Subclass this to implement a `to_dict` method which is required by serverly to pass an object as a response body"""

    def to_dict(self):
        d = {}
        for i in dir(self):
            if not i.startswith("_") and not i.endswith("_") and not callable(i) and i != "metadata" and i != "to_dict":
                a = getattr(self, i)
                if type(a) == str and a[0] == "[":
                    try:
                        a = jsonjson.loads(a)
                    except:
                        pass
                # json-serializable
                if is_json_serializable(a):
                    d[i] = a
                elif issubclass(type(a), DBObject):
                    d[i] = a.to_dict()
                elif isinstance(a, datetime.datetime):
                    d[i] = a.isoformat()
                else:
                    d[i] = str(a)
        return d


class CommunicationObject:
    """More abstract class unifying Request & Response"""

    def __init__(self, headers: dict = {}, body: Union[str, dict, list] = ""):

        self._headers = {}  # initially
        self._obj = None

        self.body = body
        self.headers = headers

    @property
    def obj(self):
        return self._obj

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers: dict):
        o = self.obj if self.obj else self.body
        try:
            self._headers = {
                **guess_response_headers(o), **self.headers, **headers}
        except TypeError:
            h = {}
            for i in headers:
                h[str(i[0], "utf-8")] = str(i[1], "utf-8")
            self._headers = {
                **guess_response_headers(o), **self.headers, **h}

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body: Union[str, dict, list, DBObject]):
        def listify(a):
            for i in a:
                b = []
                b.append(dictify(a))
                return b

        def dictify(a):
            if type(a) == dict or type(a) == list:
                try:
                    return jsonjson.dumps(a), a
                except:
                    return listify(a), a
            elif type(a) == str:
                try:
                    obj = jsonjson.loads(a)
                except jsonjson.JSONDecodeError:
                    obj = None
                return a, obj
            elif issubclass(a.__class__, DBObject):
                d = a.to_dict()
                return jsonjson.dumps(d), d
            else:
                c = a.read()
                self._headers = {
                    "Content-type": mimetypes.guess_type(a.name)[0]}
                return c, a
        self._body, self._obj = dictify(body)

    def __del__(self):
        if hasattr(self.obj, "read"):
            self.obj.close()


class Request(CommunicationObject):
    """This is passed along to registered functions as a representation of what the client requested.

    Attributes:

    - headers: dict: Headers received by client
    - body (get): String representation of requests content
    - body (set): Anything. Will be tried to jsonify, or other things if appropriate.
    - obj (get): Object representation of requests content. Might be None.
    - method: str: HTTP-Method (GET/POST etc.)
    - path: urllib.parse.ParseResult(tuple): Parsed data about the request path
    - address: tuple: Client address (e.g. ('localhost', 12345))
    - authenticated: bool: Is user authenticated (not authorized) by any means?
    - auth_type: str/None: Type of authentication (Basic/Bearer)
    - user_cred: tuple/str: Credentials of user authenticating with (e.g. ('root', 'password123') or 'somebearerstring')
    """

    def __init__(self, method: str, path: urllib.parse.ParseResult, headers: dict, body: Union[str, dict], address: tuple):
        super().__init__(headers, body)

        self.method = get_http_method_type(method)
        self.path = path
        self.address = address

        self.authenticated = False
        for key, value in self.headers.items():
            if key.lower() == "authentication" or key.lower() == "authorization":
                self.auth_type, user_cred = tuple(value.split(" "))
                if self.auth_type.lower() == "basic":
                    decoded = str(base64.b64decode(user_cred), "utf-8")
                    self.user_cred = tuple(decoded.split(":"))
                elif self.auth_type.lower() == "bearer":
                    self.user_cred = user_cred
                else:
                    self.user_cred = None
                    warnings.warn(
                        "Requested auth method not supported. Expected Basic or Bearer.")
                self.authenticated = True
        if not self.authenticated:
            self._set_auth_none()

    def _set_auth_none(self):
        self.auth_type = None
        self.user_cred = None
        self.user = None

    def __str__(self):
        s = f"{self.method.upper()}-Request from '{self.address[0]}:{str(self.address[1])}' for '{self.path.path}' with a body-length of {str(len(self.body))} and {str(len(self.headers))} headers."
        if self.auth_type != None:
            s += f" With '{self.auth_type}' authentication."
        return s


class Response(CommunicationObject):
    """You can return this from a registered function to define the response to the client

    Attributes
    ---
    - code: Response code
    - headers: dict of headers to respond to the client
    - body (get): str representation of the content
    - obj (get): Object representation of the content. Might be None.
    - body (set): Pretty much anything. Can be list, dict, string, a subclass of DBObject (e.g. serverly.user.User)
    """

    def __init__(self, code: int = 200, headers: dict = {}, body: Union[str, dict, list] = ""):
        super().__init__(headers, body)
        self.code = code

    def __str__(self):
        return f"Responding to request with a body-length of {str(len(self.body))} and {str(len(self.headers))} headers"


class Redirect(Response):
    """Behaves like a Response object. Return it to redirect client to path. If required, you can change the code from 303 - See other (GET only) to whatever you like (might not redirect of course)."""

    def __init__(self, path: str, code=303):
        super().__init__(code, {"Location": path})


class StaticSite:
    """A static using `file_path` for it's data to serve. Will be registered for `path`, if not overriden later in the process (don't *really* have to mind)"""

    def __init__(self, path: str, file_path: str):
        check_relative_path(path)
        self.file_path = check_relative_file_path(file_path)
        if path[0] != "^":
            path = "^" + path
        if path[-1] != "$":
            path += "$"
        self.path = path

    def get_content(self):
        """get content from file. Used by serverly."""
        content = ""
        if self.path == "^/error$" or self.path == "none" or self.file_path == "^/error$" or self.file_path == "none":
            content = "<html><head><title>Error</title></head><body><h1>An error occured.</h1></body></html>"
        else:
            with open(self.file_path, "r") as f:
                content = f.read()
                return Response(headers=guess_response_headers(f), body=content)


class Resource:
    """An API resource specifying how an endpoint looks. You can tell it where to sit with `__path__` and define it's endpoints in `__map__`

    Example for `__map__`:
    ```
    {
        # always return a fixed response;
        # could also be any function accepting a request and returning a response
        ('GET', '/hello'): lambda request: Response(body='hello there!'),
        ('POST', '/bye'): 'bye.html' # registers StaticSite with file path 'bye.html'
        ('GET', '/css/main.css'): StaticSite(…)
        'folders': AnotherResource # recursively!
    }
    ```
    """

    __path__ = ""
    __map__ = {}

    def use(self):
        """register endpoints specified in Resource attributes"""
        import serverly
        for k, v in self.__map__.items():
            try:
                subclass = issubclass(v, Resource)
                v = v()
            except TypeError:
                subclass = issubclass(type(v), Resource)
            if subclass:
                v.__path__ = (self.__path__ + k +
                              v.__path__).replace("//", "/")
                v.use()
                continue
            assert type(
                k) == tuple, "Expected __map__ key to a type tuple containing method and path."
            if callable(v):
                try:
                    serverly.register_function(
                        k[0], (self.__path__ + k[1]).replace("//", "/"), v)
                except Exception as e:
                    serverly.logger.handle_exception(e)
            elif type(v) == serverly.StaticSite:
                serverly._sitemap.register_site(
                    k[0], v, self.__path__ + k[1][1:])
            elif type(v) == str:
                new_path = self.__path__ + k[1]
                s = serverly.StaticSite(new_path, v)
                serverly._sitemap.register_site(k[0], s, self.__path__ + k[1])
        serverly.logger.context = "registration"
        serverly.logger.success(
            f"Registered Resource '{type(self).__name__}' for base path '{self.__path__}'.", False)


class StaticResource(Resource):
    """A subclass of StaticResource that lets you serve entire folders as (GET) endpoints. Registers endpoints on init. `folder_path` is the folder on the local filesystem to expose, `endpoint_path` the base path of all files on the web. If `file_extensions`, register the endpoints with the file extensions of the files, otherwise just the filename (might conflict with multiple filenames but different extensions)"""
    __path__ = ""
    __map__ = {}

    def __init__(self, folder_path: str, endpoint_path: str, file_extensions=True):
        self.__path__ = endpoint_path
        for dir_path, dir_names, f_names in os.walk(folder_path):
            for f in f_names:
                path = "/" + dir_path + "/" + f
                path = "/".join(path.split(".")
                                [:-1]) if not file_extensions else path
                self.__map__[("GET"), path] = StaticSite(
                    path, os.path.join(dir_path, f))
        self.use()
