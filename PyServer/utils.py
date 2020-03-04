import os


def check_relative_path(path: str):
    if type(path) == str:
        return True
    else:
        raise TypeError("'path' not valid. Expected to be of type string.")


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
            return True
        else:
            raise FileNotFoundError(f"File '{file_path}' not found.")
    else:
        raise TypeError(
            "file_path argument expected to be of type string.")
