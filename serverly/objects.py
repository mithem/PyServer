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
        try:
            self._headers = {
                **guess_response_headers(self.body), **self.headers, **headers}
        except TypeError:
            h = {}
            for i in headers:
                h[str(i[0], "utf-8")] = str(i[1], "utf-8")
            self._headers = {
                **guess_response_headers(self.body), **self.headers, **h}

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
                    self._headers = {"Content-type": "application/json"}
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
    """This is passed along to registered functions as a representation of what the client requested."""

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
        self.authorized = self.authenticated

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
    - code: response code
    - headers: dict of headers to respond to the client
    - body: str representation of the _content_
    - obj: object representation of the _content_. None if not available
    """

    def __init__(self, code: int = 200, headers: dict = {}, body: Union[str, dict, list] = ""):
        super().__init__(headers, body)
        self.code = code

    def __str__(self):
        return f"Responding to request with a body-length of {str(len(self.body))} and {str(len(self.headers))} headers"


class Redirect(Response):
    def __init__(self, path: str, code=303):
        super().__init__(code, {"Location": path})


class StaticSite:
    def __init__(self, path: str, file_path: str):
        check_relative_path(path)
        self.file_path = check_relative_file_path(file_path)
        if path[0] != "^":
            path = "^" + path
        if path[-1] != "$":
            path += "$"
        self.path = path

    def get_content(self):
        content = ""
        if self.path == "^/error$" or self.path == "none" or self.file_path == "^/error$" or self.file_path == "none":
            content = "<html><head><title>Error</title></head><body><h1>An error occured.</h1></body></html>"
        else:
            with open(self.file_path, "r") as f:
                content = f.read()
        type_ = mimetypes.guess_type(self.file_path)[0]
        return Response(headers={"Content-type": type_}, body=content)


class Resource:
    """An API resource specifying how an endpoint looks."""  # TODO documentation

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
                v.path = (self.__path__ + v.path).replace("//", "/")
                v.use()
            elif callable(v):
                try:
                    serverly.register_function(k[0], self.__path__ + k[1], v)
                except Exception as e:
                    serverly.logger.handle_exception(e)
            elif type(v) == serverly.StaticSite:
                serverly._sitemap.register_site(k[0], v, self.__path__ + k[1])
            elif type(v) == str:
                new_path = self.__path__ + k[1]
                s = serverly.StaticSite(new_path, v)
                serverly._sitemap.register_site(k[0], s, self.__path__ + k[1])
        serverly.logger.context = "registration"
        serverly.logger.success(
            f"Registered Resource '{type(self).__name__}' for base path '{self.path}'.", False)


class StaticResource(Resource):
    path = ""
    __map__ = {}

    def __init__(self, folder_path: str, file_extensions=True):
        for dir_path, dir_names, f_names in os.walk(folder_path):
            for f in f_names:
                path = "/" + dir_path + "/" + f
                path = "/".join(path.split(".")
                                [:-1]) if not file_extensions else path
                self.__map__[("GET"), path] = StaticSite(
                    path, os.path.join(dir_path, f))
        self.use()
