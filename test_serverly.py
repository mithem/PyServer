import json
import multiprocessing
import os
import time
import urllib.parse as parse

import pytest
import requests
import serverly
import serverly.objects

print("SERVERLY VERSION v" + serverly.version)
address = ("localhost", 8896)
domain = "http://" + address[0] + ":" + str(address[1])
address_available = False
database_collision = "serverly_users.db" in os.listdir()

try:
    requests.get(domain)
except requests.exceptions.ConnectionError as e:
    if "Connection refused" in str(e):
        address_available = True
except:
    pass


def test_get_server_address():
    valid = ("localhost", 8080)
    assert serverly.utils.get_server_address(("localhost", 8080)) == valid
    assert serverly.utils.get_server_address("localhost,8080") == valid
    assert serverly.utils.get_server_address("localhost, 8080") == valid
    assert serverly.utils.get_server_address("localhost;8080") == valid
    assert serverly.utils.get_server_address("localhost; 8080") == valid
    assert serverly.utils.get_server_address("localhost:8080") == valid
    assert serverly.utils.get_server_address("localhost::8080") == valid
    assert serverly.utils.get_server_address("localhost|8080") == valid
    assert serverly.utils.get_server_address("localhost||8080") == valid


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
    req = serverly.Request(
        "GET", "/helloworld", {"Content-type": "text/plain"}, content, ("localhost", 8080))
    assert req.body == content
    assert req.obj == None
    assert req.headers == {"Content-type": "text/plain"}
    assert req.address == ("localhost", 8080)
    assert req.path == "/helloworld"
    assert req.method == "get"

    assert req.auth_type == None
    assert req.user_cred == None


def test_response():
    content = "<html><h1>Hello, World</h1></html>"
    res = serverly.Response(body=content)

    assert res.headers == {"Content-type": "text/html"}
    assert res.body == content
    assert res.code == 200
    assert res.obj == None


def test_response_2():
    from serverly.user import User
    u = User()
    u.id = 1
    u.username = "oh yeah!"
    u.password = "totallyhashed"
    u.salt = "totallyrandom"
    res = serverly.Response(body=u)

    d = {
        "id": 1,
        "username": "oh yeah!",
        "password": "totallyhashed",
        "salt": "totallyrandom"
    }

    assert res.headers["Content-type"] == "application/json"

    assert res.code == 200
    assert res.obj == d

    j = json.loads(res.body)
    for k, v in j.items():
        assert d[k] == v


def test_response_3():
    d = {"hello": True, "wow": 12}

    res = serverly.Response(body=d)

    assert res.obj == d
    assert res.body == json.dumps(d)


def test_response_4():
    d = ["a", "b", "c", 4, 6, 7]

    res = serverly.Response(body=d)

    assert res.body == json.dumps(d)
    assert res.obj == d


def test_ranstr():
    s = []
    for _ in range(10000):
        r = serverly.utils.ranstr()
        assert len(r) == 20
        assert not r in s
        s.append(r)


def test_guess_response_headers():
    c1 = "<html lang='en_US'><h1>Hello World!</h1></html>"
    h1 = {"Content-type": "text/html"}
    assert serverly.utils.guess_response_headers(c1) == h1

    c2 = "Hello there!"
    h2 = {"Content-type": "text/plain"}
    assert serverly.utils.guess_response_headers(c2) == h2

    c3 = {"hello": True}
    h3 = {"Content-type": "application/json"}
    assert serverly.utils.guess_response_headers(c3) == h3

    c4 = {"id": 1, "password": "totallyhashed",
          "salt": "totallyrandom", "username": "oh yeah!"}
    h4 = {"Content-type": "application/json"}
    assert serverly.utils.guess_response_headers(c4) == h4


@pytest.mark.skipif("not address_available")
@pytest.mark.skipif("database_collision")
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

    time.sleep(5)

    evaluate()

    p.terminate()


def test_resource():
    class Test(serverly.objects.Resource):
        @staticmethod
        def a(request):
            return serverly.Response(body="on a!")

        def __init__(self):
            super().__init__()
            self.__path__ = "/test/serverly/"
            self.__map__ = {
                ("GET", "/a"): self.a,
                ("GET", "/b"): lambda request: serverly.Response(body="on b!"),
                ("GET", "/c"): serverly.objects.StaticSite("/c", "test_serverly.py")
            }

    Test().use()

    assert serverly._sitemap.get_content(serverly.Request(
        "GET", parse.urlparse("/test/serverly/a"), {}, "", ("localhost", 8091))).body == "on a!"
    assert serverly._sitemap.get_content(serverly.Request(
        "GET", parse.urlparse("/test/serverly/b"), {}, "", ("localhost", 8091))).body == "on b!"
    assert serverly._sitemap.get_content(serverly.Request(
        "GET", parse.urlparse("/test/serverly/c"), {}, "", ("localhost", 8091))).body.startswith("import ")


def test_static_resource():
    serverly.objects.StaticResource("serverly", "/folders/")

    response = serverly._sitemap.get_content(serverly.Request("GET", parse.urlparse(
        "/folders/serverly/__init__.py"), {}, "", ("localhost", 8091)))

    assert "class Sitemap" in response.body
