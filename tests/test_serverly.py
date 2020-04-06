import pytest
import serverly
import json


def test_get_server_address():
    valid = ("localhost", 8080)
    assert serverly.Server._get_server_address(
        ("localhost", 8080)) == valid
    assert serverly.Server._get_server_address("localhost,8080") == valid
    assert serverly.Server._get_server_address("localhost, 8080") == valid
    assert serverly.Server._get_server_address("localhost;8080") == valid
    assert serverly.Server._get_server_address("localhost; 8080") == valid


def test_get_server_address_2():
    valid = ("localhost", 8080)
    with pytest.raises(Exception):
        with pytest.warns(UserWarning, match="bostname and port are in the wrong order. Ideally, the addresses is a tuple[str, int]."):
            serverly.Server._get_server_address((8080, "local#ost"))


def test_sitemap():
    serverly.register_get(lambda data: ({"code": 200}, "hello world!"), "/")
    r1 = serverly.Request("GET", "/", {}, "", (0, 0))
    r2 = serverly.Request(
        "GET", "/notavalidurlactuallyitisvalid", {}, "", (0, 0))
    assert serverly._sitemap.get_content(r1).body == "hello world!"
    assert serverly._sitemap.get_content(r2).body == "404 - Page not found"


def test_request():
    content = "Hello, World!"
    req = serverly.Request("GET", "/helloworld", {"Content-type": "text/plain",
                                                  "Content-Length": len(content)}, content, ("localhost", 8080))
    assert req.body == content
    assert req.obj == None
    assert req.headers == {"Content-type": "text/plain",
                           "Content-Length": len(content)}
    assert req.address == ("localhost", 8080)
    assert req.path == "/helloworld"
    assert req.method == "get"


def test_response():
    content = "<html><h1>Hello, World</h1></html>"
    res = serverly.Response(body=content)

    assert res.headers == {"Content-type": "text/html",
                           "Content-Length": len(content)}
    assert res.body == content
    assert res.code == 200
    assert res.obj == None
