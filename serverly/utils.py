import copy
import json
import mimetypes
import os
import random
import re
import string
from typing import Union
import warnings

import serverly
import serverly.objects


def ranstr(size=20, chars=string.ascii_lowercase + string.digits + string.ascii_uppercase):
    """return a random str with length `size` with the members of `chars`, e.g. only lowercase = 'abcde...'"""
    return ''.join(random.choice(chars) for x in range(size))


def check_relative_path(path: str):
    """Check if a path is valid as a web address. Returns True if valid, else raises different kinds of errors"""
    if type(path) == str:
        if path[0] == "/" or (path[0] == "^" and path[1] == "/"):
            return True
        else:
            raise ValueError(f"'{path}' (as a path) doesn't start with '/'.")
    else:
        raise TypeError("path not valid. Expected to be of type string.")


def get_http_method_type(method: str):
    """Return lowercase http method name, if valid. Else, raise Exception."""
    supported_methods = ["get", "post", "put", "delete"  # , "head", "connect", "options", "trace", "patch"
                         ]
    m = str(method).lower()
    if not m in supported_methods:
        raise ValueError(
            f"Request method '{method}' not supported. Supported are GET, POST, PUT & DELETE.")
    return m


def check_relative_file_path(file_path: str):
    if type(file_path) == str:
        if os.path.isfile(file_path) or file_path.lower() == "none":
            return file_path
        else:
            raise FileNotFoundError(f"File '{file_path}' not found.")
    else:
        raise TypeError(
            "file_path argument expected to be of type string.")


def guess_filetype_on_filename(filename):
    return mimetypes.guess_type(filename)


def is_json_serializable(obj):
    return type(obj) == str or type(obj) == int or type(obj) == float or type(obj) == dict or type(obj) == list or type(obj) == bool or obj == None


def guess_response_headers(content):
    if type(content) == str:
        if content.startswith("<!DOCTYPE html>") or content.startswith("<html") or content.startswith("<head") or content.startswith("<body"):
            c_type = "text/html"
        else:
            c_type = "text/plain"
    elif is_json_serializable(content):
        c_type = "application/json"
    elif hasattr(content, "read"):
        c_type = mimetypes.guess_type(content.name)[0]
        if c_type == None:
            c_type = "text/plain"
    else:
        c_type = "application/octet-stream"
    return {"content-type": c_type}


def clean_user_object(user_s, *allow):
    """return cleaned version (dict!!!) of object passed in. user_s can be of type User or list[User]. *allow can be used to allow otherwise automatically removed attributes."""
    bad_attributes = ["id", "password", "salt",
                      "bearer_token", "metadata", "to_dict"]

    for i in allow:
        if i in bad_attributes:
            bad_attributes.pop(bad_attributes.index(i))

    def clean(u):
        if type(u) != list:
            return u.to_dict(bad_attributes)
        else:
            return [i.to_dict(bad_attributes) for i in u]

    return clean(user_s)


def get_server_address(address):
    """returns tupe[str, int], e.g. ('localhost', 8080)"""
    hostname = ""
    port = 0

    def valid_hostname(name):
        return bool(re.match(r"^[_a-zA-Z.-]+$", name))
    if type(address) == str:
        pattern = r"^(?P<hostname>[_a-zA-Z.-]+)((,|, |;|; |:|::|\||\|\|)(?P<port>[0-9]{2,6}))?$"
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
                raise Exception("hostname specified not valid")
    else:
        raise TypeError(
            "address argument not of valid type. Expected type[str, int] (hostname, port)")

    return (hostname, port)


def parse_scope_list(scope: str):
    r = scope.split(";")
    for i in r:
        if i == "":
            r.pop(r.index(i))
    return r


def get_scope_list(scope: Union[str, list]):
    try:
        if type(scope) == str:
            scope = [scope]
        return ";".join(scope)
    except Exception as e:
        serverly.logger.handle_exception(e)
        return ""


def parse_role_hierarchy(hierarchy: dict):
    def get_subroles(role: str):
        def expand(s: set):
            r = set()
            if type(s) == str:
                return [s]
            for i in s:
                if type(i) == set:
                    r.add(expand(i))
                else:
                    r.add(i)
            return r
        roles = set()
        for k, v in hierarchy.items():
            if k == role:
                if k == v:
                    roles.add(v)
                else:
                    [roles.add(i) for i in expand(v)]
                    [roles.add(i) for i in get_subroles(v)]
                    if type(v) == set:
                        for i in v:
                            [roles.add(j) for j in get_subroles(i)]
        return roles
    hc = {}
    for k in hierarchy:
        hc[k] = get_subroles(k)

    return hc


def get_chunked_response(response):
    def chunks(lst, n):
        """https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks"""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
    return list(chunks(response.body, response.bandwidth))


def lowercase_dict(d: dict):
    """convert all keys and values in d to lowercase (obviously str-only)"""
    new = {}
    for k, v in d.items():
        new[k.lower()] = v.lower()
    return new


def get_bytes(o, mimetype: str):
    if type(o) == str:
        return bytes(o, "utf-8")
    elif mimetype == "application/octet-stream":
        return o
    else:
        # yeah i know could be simpler, shouldn't though (will probably 'soon' become more)
        return o
