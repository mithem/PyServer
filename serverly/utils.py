import os
import json


def check_relative_path(path: str):
    if type(path) == str:
        if path[0] == "/":
            return True
        else:
            raise ValueError("path doesn't start with '/'.")
    else:
        raise TypeError("path not valid. Expected to be of type string.")


def get_http_method_type(method: str):
    if type(method) != str:
        raise TypeError(
            "method argument expected to be of type string. 'GET' and 'POST' are valid.")
    if method.lower() == "get":
        method = "get"
    elif method.lower() == "post":
        method = "post"
    else:
        raise Exception(
            "Method argument invalid. Expected 'GET' or 'POST'.")
    return method


def check_relative_file_path(file_path: str):
    if type(file_path) == str:
        if os.path.isfile(file_path) or file_path.lower() == "none":
            return file_path
        else:
            raise FileNotFoundError(f"File '{file_path}' not found.")
    else:
        raise TypeError(
            "file_path argument expected to be of type string.")


def parse_response_info(info: dict, content_length=0):
    response_code = 200
    content_length = content_length
    content_type = "text/plain"
    overflow = {}
    for key, value in info.items():
        if key.lower() == "response_code" or key.lower() == "response code" or key.lower() == "code" or key.lower() == "response" or key.lower() == "responsecode":
            response_code = value
        elif key.lower() == "content-length" or key.lower() == "content_length" or key.lower() == "content length" or key.lower() == "length":
            content_length = value
        elif key.lower() == "content-type" or key.lower() == "content_type" or key.lower() == "content type" or key.lower() == "type":
            content_type = value
        else:
            overflow[key] = value
    info = {"Content-Length": content_length,
            "Content-type": content_type, **overflow}
    return response_code, info


def guess_response_info(content: str):
    if content.startswith("<DOCTYPE html>") or content.startswith("<html"):
        c_type = "text/html"
    else:
        try:
            json.loads(content)
            c_type = "application/json"
        except json.JSONDecodeError:
            c_type = "text/plain"
    return 200, {"Content-type": c_type, "Content-Length": len(content)}
