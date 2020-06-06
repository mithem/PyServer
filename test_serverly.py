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


def test_sitemap():
    def hello_world(req):
        return serverly.Response(body="hello world!")
    serverly.register_function("GET", "/", hello_world)
    r1 = serverly.Request("GET", parse.urlparse("/"), {}, "", (0, 0))
    r2 = serverly.Request(
        "GET", parse.urlparse("/notavalidurlactuallyitisvalid"), {}, "", (0, 0))
    assert serverly._sitemap.get_content(r1)[1].body == "hello world!"
    assert "404 - Page not found" in serverly._sitemap.get_content(r2)[1].body


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
                ("GET", "/c"): serverly.objects.StaticSite("/c", "setup.py"),
                ("GET", "/d"): "test_serverly.py"
            }

    Test().use()

    assert serverly._sitemap.get_content(serverly.Request(
        "GET", parse.urlparse("/test/serverly/a"), {}, "", ("localhost", 8091)))[1].body == "on a!"
    assert serverly._sitemap.get_content(serverly.Request(
        "GET", parse.urlparse("/test/serverly/b"), {}, "", ("localhost", 8091)))[1].body == "on b!"
    assert serverly._sitemap.get_content(serverly.Request(
        "GET", parse.urlparse("/test/serverly/c"), {}, "", ("localhost", 8091)))[1].body.startswith("import ")
    assert serverly._sitemap.get_content(serverly.Request("GET", parse.urlparse(
        "/test/serverly/d"), {}, "", ("localhost", 8091)))[1].body.startswith("import ")


def test_static_resource():
    serverly.objects.StaticResource("serverly", "/folders/")

    response = serverly._sitemap.get_content(serverly.Request("GET", parse.urlparse(
        "/folders/serverly/__init__.py"), {}, "", ("localhost", 8091)))[1]

    assert "class Sitemap" in response.body
