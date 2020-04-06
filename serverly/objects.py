import json as jsonjson
from typing import Union

from serverly.utils import get_http_method_type, guess_response_info


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
        self._headers = {**guess_response_info(self.body), **headers}

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, body: Union[str, dict, list]):
        if type(body) == dict or type(body) == list:
            self._obj = body
            self._body = jsonjson.dumps(body)
        elif type(body) == str:
            self._body = body
            try:
                self._obj = jsonjson.loads(body)
            except jsonjson.JSONDecodeError:
                self._obj = None


class Request(CommunicationObject):
    """This is passed along to registered functions as a representation of what the client requested."""

    def __init__(self, method: str, path: str, headers: dict, body: Union[str, dict], address: tuple):
        super().__init__(headers, body)

        self.method = get_http_method_type(method)
        self.path = path
        self.address = address

    def __str__(self):
        return f"{self.method.upper()}-Request from '{self.address[0]}:{str(self.address[1])}' for '{self.path}' with a body-length of {str(len(self.body))} and {str(len(self.headers))} headers"


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
