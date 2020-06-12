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
        print("avail")
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

    time.sleep(0.5)

    evaluate()

    p.terminate()
