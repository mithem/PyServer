import pytest
import serverly
import json
import urllib.parse as parse
import multiprocessing
import requests

print("SERVERLY VERSION v" + serverly.version)
address = "localhost", 8896
domain = "http://" + address[0] + ":" + str(address[1])
address_available = False

try:
    requests.get(domain)
except requests.exceptions.ConnectionError as e:
    if "Connection refused" in str(e):
        address_available = True
except:
    pass


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


@pytest.mark.skip
@pytest.mark.skipif("not address_available")
def test_server():
    serverly.address = address

    @serverly.serves("GET", "/")
    @serverly.serves("GET", "/index")
    def hello(req):
        return serverly.objects.Response(body="Hello from pytest!")

    @serverly.serves("POST", "/func2")
    def func2():
        return serverly.objects.Response()

    @serverly.serves("PUT", "/erroorr")
    def falsy(req):
        raise NotImplementedError("yo what?")

    def evaluate():
        r = requests.get(domain)
        r2 = requests.get(domain + "/index")
        r3 = requests.post(domain + "/func2")
        r4 = requests.put(domain + "/erroorr")

        assert r.status_code == 200
        assert r.text == "Hello from pytest!"

        assert r2.status_code == r.status_code
        assert r2.text == r.text

        assert r3.status_code == 200
        assert r3.text == ""

        assert r4.status_code == 500
        assert "Sorry, something went wrong on our side." in r4.text and "500 - Internal server error" in r4.text

    p = multiprocessing.Process(target=serverly.start)

    p.start()

    evaluate()

    p.terminate()
