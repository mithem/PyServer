import base64
import datetime
import hashlib
import os
import re
import time
import urllib.parse as parse
import warnings
from typing import Union

import pytest
import serverly
import serverly.user as user
import serverly.user.auth as auth
import serverly.user.session
import serverly.utils
import sqlalchemy
from serverly.objects import Request, Response, DBObject

print("SERVERLY VERSION v" + serverly.version)

FILENAME = "test_user.py.db"
database_collision = "serverly_users.db" in os.listdir()
serverly.user.session_renew_threshold = 1


try:
    os.remove(FILENAME)
except:
    pass


def clear_setup():
    user._engine = None
    user._Session = None
    user.algorithm = None
    user.salting = 1


@pytest.mark.skipif("user._engine != None")  # already set up
def test_setup():
    assert user._engine == None
    assert user._Session == None
    assert user.algorithm == None
    assert user.salting == 1

    user.setup(filename=FILENAME, user_columns={
               "first_name": str, "email": str, "role": (str, "normal")})

    assert type(user._engine) == sqlalchemy.engine.base.Engine
    assert type(user._Session) == sqlalchemy.orm.session.sessionmaker
    assert user.algorithm == hashlib.sha3_512
    assert user.salting == 1

    clear_setup()


# cannot specify filename for implicit setup, therfore it can collide with the other db (serverly_users.db)
@pytest.mark.skipif("database_collision")
def test_setup_required():

    @user._setup_required
    def part_of_the_test():
        pass

    assert user._engine == None
    assert user._Session == None
    assert user.algorithm == None
    assert user.salting == 1

    part_of_the_test()

    assert type(user._engine) == sqlalchemy.engine.base.Engine
    assert type(user._Session) == sqlalchemy.orm.session.sessionmaker
    assert user.algorithm == hashlib.sha3_512
    assert user.salting == 1


def test_mockup_hash_algorithm():
    assert user.mockup_hash_algorithm(
        bytes("hello world!", "utf-8")).hexdigest() == "hello world!"


@pytest.mark.skipif("database_collision")
def test_get_all():
    assert len(user.get_all()) == 0


@pytest.mark.skipif("database_collision")
def test_register():
    user.register("temporary", "temporary", first_name="Hello")
    assert len(user.get_all()) == 1


def test_authenticate():
    try:
        assert user.authenticate("temporary", "temporary")
        assert not user.authenticate("temporary", "notcorrect")

        assert user.authenticate("temporary", "temporary", True)
    except user.UserNotFoundError:
        pass  # if this test is run seperately, authenticate will not find the user
    with pytest.raises(user.UserNotFoundError):
        user.authenticate("definetelynotanamebyanymeans", "dontcare:)", True)
    with pytest.raises(user.NotAuthorizedError):
        user.authenticate("temporary", "notcorrect", True)


def test_clean_user_object():
    u = user.User()
    u.id = 0
    u.password = "dnsakjrßheönocuq3öoiewjOurcqwrPOevuiä3u"
    u.salt = "wdaiurjelkcbcjvkerkjwvegröui"
    u.username = "helloworld"
    u.bearer_token = serverly.utils.ranstr(50)
    u.birth_year = 1970
    u.first_name = "Timmy"
    n = serverly.utils.clean_user_object(u)
    assert n == {"username": "helloworld",
                 "birth_year": 1970, "first_name": "Timmy", "email": None, "role": None}


def test_clean_user_object_2():

    bad_attributes = ["id", "password", "salt"]

    def get_new():
        u = user.User()
        u.id = 0
        u.password = serverly.utils.ranstr()
        u.salt = serverly.utils.ranstr()
        u.username = serverly.utils.ranstr()
        u.birth_year = 1985
        u.first_name = "Tom"
        return u

    l = []
    for i in range(100):
        l.append(get_new())

    cleaned = serverly.utils.clean_user_object(l)

    for u in cleaned:
        for ba in bad_attributes:
            with pytest.raises(AttributeError):
                getattr(u, ba)


def test_clean_user_object_3():
    class MockupClass(DBObject):
        a = 10
        b = True
        c = 3.14
        id = 99
        password = "somepassword"
        salt = "somesalt"

    assert serverly.utils.clean_user_object(MockupClass()) == {
        "a": 10, "b": True, "c": 3.14}

    assert serverly.utils.clean_user_object([MockupClass() for _ in range(10)]) == [{
        "a": 10, "b": True, "c": 3.14} for _ in range(10)]


@pytest.mark.skipif("database_collision")
def test_clean_user_object_3():
    import serverly.user.auth
    d = datetime.datetime.now() + datetime.timedelta(minutes=30)
    i = d.isoformat()
    t1 = serverly.user.auth.get_new_token(
        "temporary", "read", d)
    t2 = serverly.user.auth.get_new_token("temporary", "write", d)

    n = serverly.utils.clean_user_object(
        [t1, t2], "id", "notanattributeanyway")

    a = [{"username": "temporary", "expires": i,
          "scope": "read", "value": t1.value, "id": 1}, {"username": "temporary", "expires": i, "scope": "write", "value": t2.value, "id": 2}
         ]

    for i in a:
        assert i in n

# auth tests


def g(auth_type: str, auth_data: Union[tuple, str], b64_encode=False):
    if auth_data != None:
        auth_header_value = auth_type + " "
        if type(auth_data) == tuple:
            auth_data = auth_data[0] + ":" + auth_data[1]
        if b64_encode == False:
            auth_header_value += auth_data
        else:
            auth_header_value += str(base64.b64encode(
                bytes(auth_data, "utf-8")), "utf-8")
        h = {"authorization": auth_header_value}
    else:
        h = {}
    return Request("get", parse.urlparse("/hello"), h, "No real body", ("localhost", 2020))


def compare(r1: Response, r2: Response):
    print("r1:", r1.body)
    print("r2:", r2.body)
    assert r1.code == r2.code
    assert r1.headers == r2.headers
    assert bool(re.match(r2.body, r1.body))


valid = Response(body="success!")

invalid_auth = Response(
    401, {"content-type": "text/plain"}, "Unauthorized.")

user_not_found = Response(
    404, {"content-type": "text/plain"}, "^User \'[\w]+\' not found.$")


def no_auth(auth_type: str):
    return Response(401, {"content-type": "text/plain",
                          "www-authenticate": auth_type}, "Unauthorized.")


def test_basic_auth():
    @auth.basic_auth
    def success(req: Request):
        u = serverly.user.get("temporary")
        assert req.user.username == u.username
        assert req.user.email == u.email
        assert req.user.salt == u.salt
        return valid

    r = success(g("basic", ("temporary", "temporary"), True))
    compare(r, valid)

    r = success(g("basic", ("temporary", "invalid"), True))
    compare(r, invalid_auth)

    r = success(g("basic", None))
    compare(r, no_auth("basic"))

    r = success(g("basic", ("invalid", "unimportant"), True))
    compare(r, user_not_found)

    r = success(g("bearer", "hellothere"))
    compare(r, invalid_auth)

    r = success(g(None, None))
    compare(r, no_auth("basic"))


def test_bearer_auth():
    valid_bearer_token = auth.get_new_token("temporary").value
    @auth.bearer_auth("")
    def success(req: Request):
        u = serverly.user.get("temporary")
        assert req.user.username == u.username
        assert req.user.email == u.email
        assert req.user.salt == u.salt
        return valid

    r = success(g("bearer", valid_bearer_token))
    compare(r, valid)

    r = success(g("bearer", "someinvalidtokenstr"))
    compare(r, invalid_auth)

    r = success(g("basic", ("temporary", "temporary"), True))
    compare(r, no_auth("bearer"))

    r = success(g(None, None))
    compare(r, no_auth("bearer"))

    r = success(g("bearer", None))
    compare(r, no_auth("bearer"))

    r = success(g("bearer", ""))
    compare(r, no_auth("bearer"))


def test_session_auth():
    valid_bearer_token = auth.get_new_token("temporary").value
    serverly.user.session.new_activity("temporary", ("localhost", 8080))
    @auth.session_auth("")
    def success(req: Request):
        u = serverly.user.get("temporary")
        assert req.user.username == u.username
        assert req, user.email == u.email
        assert req.user.salt == u.salt
        return valid

    r = success(g("bearer", valid_bearer_token))
    compare(r, valid)

    time.sleep(serverly.user.session_renew_threshold * 2)

    r = success(g("bearer", valid_bearer_token))
    compare(r, invalid_auth)


def test_valid_token():
    wait = 0.1

    d = datetime.datetime.now()
    t = d + datetime.timedelta(seconds=wait)

    token = auth.get_new_token("temporary")
    assert auth.valid_token(token)
    assert not auth.valid_token(token, scope="write")
    assert auth.valid_token(token.value)

    token = auth.get_new_token("temporary", "write")
    assert auth.valid_token(token)
    assert auth.valid_token(token, scope="write")
    assert not auth.valid_token(token, scope="read")

    token = auth.get_new_token("temporary", expires=t)
    assert auth.valid_token(token)

    time.sleep(wait)
    assert not auth.valid_token(token)


def test_clear_expired_tokens():
    assert auth.clear_expired_tokens() == 1


def test_get_tokens_by_user():
    assert len(auth.get_tokens_by_user("temporary")) > 0


def test_clear_all():
    assert len(auth.get_all_tokens()) > 0
    auth.clear_all_tokens()
    assert len(auth.get_all_tokens()) == 0
