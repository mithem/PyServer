import base64 as b64
import datetime
import json
import os
import urllib.parse as parse

import pytest
import serverly
from serverly.objects import (DBObject, Redirect, Request, Resource, Response,
                              StaticSite)


def test_request():
    content = "Hello, World!"
    req = Request(
        "GET", parse.urlparse("/helloworld"), {"content-type": "text/plain"}, content, ("localhost", 8080))
    assert req.body == content
    assert req.obj == None
    assert req.headers == {"content-type": "text/plain"}
    assert req.address == ("localhost", 8080)
    assert req.path.path == "/helloworld"
    assert req.method == "get"

    assert req.auth_type == None
    assert req.user_cred == None


def test_request_2():
    req = Request("GET", parse.urlparse("/whatever/path/this/is"),
                  {"AutheNtiCation": "Basic " + b64.b64encode("myuser:mypassword".encode("utf-8")).decode("utf-8")}, "", ("localhost", 8080))

    assert req.auth_type == "basic"
    assert req.user_cred == ("myuser", "mypassword")


def test_request_3():
    req = Request("GET", parse.urlparse("/some/path"),
                  {"Authentication": "Basic jfalksjflekabdlb"}, "Hello there", ("localhost", 9999))
    assert req.auth_type == None
    assert req.user_cred == None


def test_request_4():
    req = Request("GET", parse.urlparse("/another/path"),
                  {"Authentication": "Bearer abc"}, "", ("localhost", 9999))

    assert req.auth_type == "bearer"
    assert req.user_cred == "abc"


def test_request_5(capsys):
    req = Request("GET", parse.urlparse("/once/again"),
                  {"Authentication": "notreallythere abc"}, "", ("localhost", 9999))

    assert req.auth_type == None
    assert req.user_cred == None

    assert "Requested auth method not supported." in capsys.readouterr().out


def test_request_6():
    req = Request("GET", parse.urlparse("/last/path?probably=not"),
                  {"Some unimportant header": "and it's value", "Content-type": "dunno?"}, "The body", ("localhost", 8090))
    s = "GET-Request from 'localhost:8090' for '/last/path' with a body-length of 8 and 2 headers."

    assert str(req) == s

    req = Request("GET", parse.urlparse("/last/path?probably=not"),
                  {"Authentication": "bearer abc"}, "The body", ("localhost", 8090))
    assert str(req) == s + " With 'bearer' authentication."


def test_response():
    content = "<html><h1>Hello, World</h1></html>"
    res = Response(body=content)

    assert res.headers == {"content-type": "text/html"}
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
    res = Response(body=u)

    d = {
        "id": 1,
        "username": "oh yeah!",
        "password": "totallyhashed",
        "salt": "totallyrandom"
    }

    assert res.headers["content-type"] == "application/json"

    assert res.code == 200
    assert res.obj == d

    j = json.loads(res.body)
    for k, v in j.items():
        assert d[k] == v


def test_response_3():
    d = {"hello": True, "wow": 12}

    res = Response(body=d)

    assert res.obj == d
    assert res.body == json.dumps(d)


def test_response_4():
    d = ["a", "b", "c", 4, 6, 7]

    res = Response(body=d)

    assert res.body == json.dumps(d)
    assert res.obj == d


def test_response_5():
    f = open("test_serverly.py", "r")
    c = f.read()
    r = Response(body=f)
    assert r.obj.name == "test_serverly.py"
    assert c.startswith("import ")
    assert r.body == c


def test_response_6():
    class MockupClass(DBObject):
        a = True
        b = 10
        c = 3.14
    r = Response(body=[MockupClass(), MockupClass()])
    d = {"a": True, "b": 10, "c": 3.14}
    assert r.obj == [d, d]


def test_redirect():
    r = Redirect("/index")
    assert r.code == 303
    assert r.headers["location"] == "/index"


def test_StaticSite():
    with open("temporary", "wb+") as f:
        f.write(os.urandom(10))
    s = StaticSite("/somefile", "temporary")
    f = s.get_content().obj
    assert f.name == "temporary"
    assert f.mode == "rb"
    f.close()
    os.remove("temporary")


def test_StaticSite():
    assert serverly._sitemap.methods["get"].get("^/mypath$", None) == None

    StaticSite("/mypath", "test_objects.py").use()

    assert isinstance(serverly._sitemap.methods["get"].get(
        "^/mypath$", None), StaticSite)


def test_DBObject():
    o = DBObject()
    o.hello = True
    o.test = "hello world"
    o.list = [1, 2, 3, "hello", "there"]
    o.strlist = "[1, 2, 3]"
    o.falsystrlist = "[1, 2, 'hello']"
    o.emptystr = ""
    assert o.to_dict() == {"hello": True, "test": "hello world", "list": [
        1, 2, 3, "hello", "there"], "strlist": [1, 2, 3], "falsystrlist": "[1, 2, 'hello']", "emptystr": ""}


def test_DBObject_2():
    class MockupClass:
        def __str__(self):
            return "Hello world!"
    d = datetime.datetime.now()
    o = DBObject()
    a = DBObject()
    a.name = "hello world"
    o.child = a
    o.date = d
    o.cls = MockupClass()
    assert o.to_dict() == {
        "child": {"name": "hello world"}, "date": d.isoformat(), "cls": "Hello world!"}


def test_resource():
    class Mini(Resource):
        __path__ = "/mini/"
        __map__ = {
            ('GET', '/cooper'): "test_objects.py"
        }

    class Test(Resource):
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
                ("GET", "/d"): "test_serverly.py",
                "/mini": Mini
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
    response = serverly._sitemap.get_content(serverly.Request("GET", parse.urlparse(
        "/test/serverly/mini/cooper"), {}, "", ("localhost", 8091)))[1]


def test_static_resource():
    serverly.objects.StaticResource("serverly", "/folders/")

    response = serverly._sitemap.get_content(serverly.Request("GET", parse.urlparse(
        "/folders/serverly/__init__.py"), {}, "", ("localhost", 8091)))[1]

    assert "class Sitemap" in response.body
