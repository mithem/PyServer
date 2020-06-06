import json

from serverly.objects import Request, Resource, Response, StaticSite


def test_request():
    content = "Hello, World!"
    req = Request(
        "GET", "/helloworld", {"content-type": "text/plain"}, content, ("localhost", 8080))
    assert req.body == content
    assert req.obj == None
    assert req.headers == {"content-type": "text/plain"}
    assert req.address == ("localhost", 8080)
    assert req.path == "/helloworld"
    assert req.method == "get"

    assert req.auth_type == None
    assert req.user_cred == None


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

