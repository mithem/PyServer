import pytest
import serverly.utils
from serverly.utils import *


def test_parse_role_hierarchy():
    e1 = {
        "normal": "normal",
        "admin": "normal"
    }
    e2 = {
        "normal": "normal",
        "admin": "normal",
        "staff": "admin",
        "root": "staff",
        "god": "staff",
    }
    e3 = {
        "normal": "normal",
        "admin": "normal",
        "staff": "normal",
        "root": {"admin", "staff"},
        "god": "root"
    }

    r1 = parse_role_hierarchy(e1)
    r2 = parse_role_hierarchy(e2)
    r3 = parse_role_hierarchy(e3)

    assert r1 == {"normal": {"normal"}, "admin": {"normal"}}
    assert r2 == {"normal": {"normal"}, "admin": {"normal"}, "staff": {
        "admin", "normal"}, "root": {"admin", "normal", "staff"}, "god": {"admin", "normal", "staff"}}
    assert r3 == {"normal": {"normal"}, "admin": {"normal"},
                  "staff": {"normal"}, "root": {"admin", "normal", "staff"}, "god": {"admin", "normal", "staff", "root"}}


def test_ranstr():
    s = []
    for _ in range(10000):
        r = ranstr()
        assert len(r) == 20
        assert not r in s
        s.append(r)


def test_guess_response_headers():
    c1 = "<html lang='en_US'><h1>Hello World!</h1></html>"
    h1 = {"content-type": "text/html"}
    assert guess_response_headers(c1) == h1

    c2 = "Hello there!"
    h2 = {"content-type": "text/plain"}
    assert guess_response_headers(c2) == h2

    c3 = {"hello": True}
    h3 = {"content-type": "application/json"}
    assert guess_response_headers(c3) == h3

    c4 = {"id": 1, "password": "totallyhashed",
          "salt": "totallyrandom", "username": "oh yeah!"}
    h4 = {"content-type": "application/json"}
    assert guess_response_headers(c4) == h4

    c5 = open("test_utils.py", "r")
    h5 = {"content-type": "text/x-python"}
    assert guess_response_headers(c5) == h5
    c5.close()

    c6 = open("temporary.md", "w+")
    h6 = {"content-type": "text/plain"}
    assert guess_response_headers(c6) == h6
    c6.close()
    os.remove("temporary.md")

    c7 = bytes("hello world", "utf-8")
    h7 = {"content-type": "application/octet-stream"}
    assert guess_response_headers(c7) == h7


def test_get_server_address():
    valid = ("localhost", 8080)

    assert get_server_address(("localhost", 8080)) == valid
    assert get_server_address("localhost,8080") == valid
    assert get_server_address("localhost, 8080") == valid
    assert get_server_address("localhost;8080") == valid
    assert get_server_address("localhost; 8080") == valid
    assert get_server_address("localhost:8080") == valid
    assert get_server_address("localhost::8080") == valid
    assert get_server_address("localhost|8080") == valid
    assert get_server_address("localhost||8080") == valid


def test_get_server_address_2():
    valid = ("localhost", 20000)
    typy_errory = [True, {"hostname": "localhost", "port": 20000}, 42]
    value_errory = [(True, "localhost"), ("whats", "up"), (42, 3.1415926535)]

    assert get_server_address((20000, "localhost")) == valid

    for i in typy_errory:
        with pytest.raises(TypeError):
            get_server_address(i)

    for i in value_errory:
        with pytest.raises(ValueError):
            get_server_address(i)


def test_get_server_address_3():
    valid = ("localhost", 8080)
    with pytest.raises(Exception):
        with pytest.warns(UserWarning):
            serverly.Server._get_server_address((8080, "local#ost"))


def test_check_relative_path():
    falsy_values = ["hello", "whatsupp", ""]
    typy_errors = [bytes("hello there", "utf-8"),
                   open("test_utils.py", "r"), True, 23.7]
    goodish_ones = ["/hello", "/hello-world", "/whatss/up"]

    for i in falsy_values:
        with pytest.raises(ValueError):
            check_relative_path(i)

    for i in typy_errors:
        with pytest.raises(TypeError):
            check_relative_path(i)

    for i in goodish_ones:
        assert check_relative_path(i)


def test_check_relative_file_path():
    with pytest.raises(FileNotFoundError):
        check_relative_file_path(
            "definetelynotafile.definetelynotafile.definetelynotafile!")

    bad_ones = [True, open("test_utils.py", "r"), 42]
    for i in bad_ones:
        with pytest.raises(TypeError):
            check_relative_file_path(i)

    assert check_relative_file_path("test_utils.py") == "test_utils.py"


def test_get_http_method_type():
    false_ones = ["GETT", "PooST", "puUT", "DEL", "del",
                  "head", "CONNECT", "options", "TRACE", "patch"]
    good_ones = {"GET": "get", "PoSt": "post",
                 "Put": "put", "DelEtE": "delete"}

    for i in false_ones:
        with pytest.raises(ValueError):
            get_http_method_type(i)
            print(i)

    for k, v in good_ones.items():
        assert get_http_method_type(k) == v


def test_parse_scope_list():
    assert parse_scope_list("hello;world;whatsup") == [
        "hello", "world", "whatsup"]
    assert parse_scope_list("19;") == ['19']
    assert parse_scope_list("42;1829;sajki;") == ["42", "1829", "sajki"]
    assert parse_scope_list("") == []


def test_get_scope_list():
    assert get_scope_list("admin") == "admin"
    assert get_scope_list(["admin", "financial"]) == "admin;financial"
    assert get_scope_list("") == ""


def test_get_chunked_response():
    r = serverly.objects.Response(body="Hello world")
    assert get_chunked_response(r) == ["Hello world"]

    r.bandwidth = 4
    assert get_chunked_response(r) == ["Hell", "o wo", "rld"]


def test_lowercase_dict():
    d = {"Hello World": True, "WhatssUpp": "Yoo"}
    assert lowercase_dict(d) == {"hello world": True, "whatssupp": "Yoo"}
    assert lowercase_dict(d, True) == {"hello world": True, "whatssupp": "yoo"}


def test_get_bytes():
    assert get_bytes("hello world") == bytes("hello world", "utf-8")
    assert get_bytes(
        "hello world", "application/octet-stream") == b"hello world"
    assert get_bytes(
        {"helele": 42}, "application/octet-stream") == {"helele": 42}
    assert get_bytes(True) == True
