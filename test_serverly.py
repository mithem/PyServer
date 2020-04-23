import pytest
import serverly
import json
import urllib.parse as parse

print("SERVERLY VERSION v" + serverly.version)


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
    def hello_world(req):
        return serverly.Response(body="hello world!")
    serverly.register_function("GET", "/", hello_world)
    r1 = serverly.Request("GET", parse.urlparse("/"), {}, "", (0, 0))
    r2 = serverly.Request(
        "GET", parse.urlparse("/notavalidurlactuallyitisvalid"), {}, "", (0, 0))
    assert serverly._sitemap.get_content(r1).body == "hello world!"
    assert "404 - Page not found" in serverly._sitemap.get_content(r2).body


def test_request():
    content = "Hello, World!"
    cl = len(content)
    req = serverly.Request("GET", "/helloworld", {"Content-type": "text/plain",
                                                  "Content-Length": cl}, content, ("localhost", 8080))
    assert req.body == content
    assert req.obj == None
    assert req.headers == {"Content-type": "text/plain",
                           "Content-Length": cl}
    assert req.address == ("localhost", 8080)
    assert req.path == "/helloworld"
    assert req.method == "get"

    assert req.auth_type == None
    assert req.user_cred == None


def test_response():
    content = "<html><h1>Hello, World</h1></html>"
    res = serverly.Response(body=content)

    assert res.headers == {"Content-type": "text/html",
                           "Content-Length": len(content)}
    assert res.body == content
    assert res.code == 200
    assert res.obj == None


def test_ranstr():
    for _ in range(100):
        assert len(serverly.utils.ranstr()) == 20
