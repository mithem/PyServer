import base64
import collections.abc
import datetime
import json as jsonjson
import mimetypes
import os
import urllib.parse
from typing import Union

import serverly
from serverly.utils import (check_relative_file_path, check_relative_path,
                            get_http_method_type, guess_response_headers,
                            is_json_serializable, lowercase_dict, clean_user_object)


class DBObject:
    """Subclass this to implement a `to_dict` method which is required by serverly to pass an object as a response body"""

    def to_dict(self, forbidden=[]):
        d = {}
        for i in dir(self):
            if not i.startswith("_") and not i.endswith("_") and not callable(i) and i != "metadata" and i != "to_dict" and not i in forbidden:
                a = getattr(self, i)
                try:
                    if type(a) == str and a[0] == "[":
                        try:
                            a = jsonjson.loads(a)
                        except:
                            pass
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
            self._headers = lowercase_dict({
                **guess_response_headers(o), **self.headers, **headers})
        except TypeError:
            h = {}
            for i in headers:
                h[str(i[0], "utf-8")] = str(i[1], "utf-8")
            self._headers = lowercase_dict({
                **guess_response_headers(o), **self.headers, **h})

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body: Union[str, dict, list, DBObject]):
        """str, dict, list, DBObject (or subclass) or file-like object"""
        def dictify(a):
            if type(a) == list:
                try:
                    return jsonjson.dumps(a), a
                except:
                    b = [dictify(i)[1] for i in a]
                    return jsonjson.dumps(b), b
            elif type(a) == dict:
                return jsonjson.dumps(a), a
            elif type(a) == str:
                try:
                    obj = jsonjson.loads(a)
                except jsonjson.JSONDecodeError:
                    obj = None
                return a, obj
            elif issubclass(a.__class__, DBObject):
                b = clean_user_object(a)
                return jsonjson.dumps(b), b
            else:
                a.seek(0)
                c = a.read()
                self._headers["content-type"] = mimetypes.guess_type(a.name)[
                    0]
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
        try:
            for key, value in self.headers.items():
                kl = key.lower()
                if kl == "authentication" or kl == "authorization":
                    auth = tuple(value.split(" "))
                    self.auth_type = auth[0].lower()
                    user_cred = auth[1]
                    if self.auth_type == "basic":
                        try:
                            decoded = str(base64.b64decode(user_cred), "utf-8")
                            self.user_cred = tuple(decoded.split(":"))
                            self.authenticated = True
                        except UnicodeDecodeError as e:
                            serverly.logger.handle_exception(e)
                            break
                    elif self.auth_type == "bearer":
                        self.user_cred = user_cred
                        self.authenticated = True
                    else:
                        try:
                            raise Warning(
                                "Requested auth method not supported. Expected basic or bearer.")
                        except Warning as e:
                            serverly.logger.show_warning(e)
        except Exception as e:
            serverly.logger.handle_exception(e)
            self._set_auth_none()
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
    - bandwidth: Maximum bandwidth used when sending to client (**bytes per sec**). None for no regulation.
    """

    def __init__(self, code: int = 200, headers: dict = {}, body: Union[str, dict, list] = "", bandwidth: int = None):
        try:
            super().__init__(headers, body)
            self.code = code
            self.bandwidth = bandwidth
        except Exception as e:
            serverly.logger.handle_exception(e)

    def __str__(self):
        return f"Responding to request with a body-length of {str(len(self.body))} and {str(len(self.headers))} headers"


class Redirect(Response):
    """Behaves like a Response object. Return it to redirect client to path. If required, you can change the code from 303 - See other (GET only) to whatever you like (might not redirect of course)."""

    def __init__(self, path: str, code=303, **extra_headers):
        super().__init__(code, {"location": path, **extra_headers})


class StaticSite:
    """A static site using `file_path` for it's data to serve. Will be registered for `path` (if you register it), if not overriden in the process (don't *really* have to mind). Instead registering it manually, you can call `.use()`."""

    def __init__(self, path: str, file_path: str):
        check_relative_path(path)
        self.file_path = check_relative_file_path(file_path)
        path = path.replace("//", "/")
        if path[0] != "^":
            path = "^" + path
        if path[-1] != "$":
            path += "$"
        self.path = path

    def get_content(self):
        """get content from file. Used by serverly."""
        try:
            f = open(self.file_path, "r")
            f.seek(0)
            f.read()
        except UnicodeDecodeError:
            f = open(self.file_path, "rb")
        return Response(body=f)

    def use(self):
        """register it, so you don't have to"""
        serverly._sitemap.register_site("GET", self)

    def __str__(self):
        return f"StaticSite ({self.path})"


class Resource:
    """An API resource specifying how an endpoint looks. You can tell it where to sit with `__path__` and define it's endpoints in `__map__`

    Example for `__map__`:
    ```
    {
        # always return a fixed response;
        # could also be any function accepting a request and returning a response
        ('GET', '/hello'): lambda request: Response(body='hello there!'),
        # registers StaticSite with file path 'bye.html'
        ('POST', '/bye'): 'bye.html'
        ('GET', '/css/main.css'): StaticSite(…)
        'folders': AnotherResource # recursively!
    }
    ```
    """

    __path__ = ""
    __map__ = {}

    def use(self):
        """register endpoints specified in Resource attributes"""
        for k, v in self.__map__.items():
            try:
                subclass = issubclass(v, Resource)
                v = v()
            except TypeError:
                subclass = issubclass(type(v), Resource)
            if subclass:
                v.__path__ = (self.__path__ + k).replace("//", "/")
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
                serverly._sitemap.register_site(
                    k[0], s, new_path.replace("//", "/"))
        serverly.logger.context = "registration"
        serverly.logger.success(
            f"Registered Resource '{type(self).__name__}' for base path '{self.__path__}'.", False)


class StaticResource(Resource):
    """A subclass of StaticResource that lets you serve entire folders as (GET) endpoints. Registers endpoints on init. `folder_path` is the folder on the local filesystem to expose, `endpoint_path` the base path of all files on the web. If `file_extensions`, register the endpoints with the file extensions of the files, otherwise just the filename (might conflict with multiple filenames but different extensions). 

    Note: The folder name will be included in all paths.

    Example:

    Assuming the following folder structure
    ```txt
    - my_server_file.py
    - hello
      - hello.txt
      - what
        - dunno_what_to_name_this.txt
    ```

    , after calling `StaticResource('hello', '/myfolder/')`, the following (GET) endpoints will (hopefully) be registered:

    - /myfolder/hello/hello.txt
    - /myfolder/hello/what/dunno_what_to_name_this.txt

    In case you set `file_extensions=False`, this will be served:

    - /myfolder/hello/hello
    - /myfolder/hello/what/dunno_what_to_name_this
    """
    __path__ = ""
    __map__ = {}

    def __init__(self, folder_path: str, endpoint_path: str, file_extensions=True):
        self.__path__ = endpoint_path
        for dir_path, dir_names, f_names in os.walk(folder_path):
            for f in f_names:
                path = "/" + dir_path + "/" + f
                path = "/".join(path.split(".")
                                [:-1]) if not file_extensions else path
                self.__map__[("GET", path)] = StaticSite(
                    (endpoint_path + "/" + path).replace("//", "/"), os.path.join(dir_path, f))
        self.use()
