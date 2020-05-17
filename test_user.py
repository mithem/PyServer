import datetime
import hashlib
import os
import warnings

import pytest
import serverly
import serverly.user as user
import serverly.utils
import sqlalchemy

print("SERVERLY VERSION v" + serverly.version)

FILENAME = "test_user.py.db"
database_collision = "serverly_users.db" in os.listdir()

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
               "first_name": str, "email": str, "bearer_token": str, "role": (str, "normal")})

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


@pytest.mark.skipif("database_collision")
def test_clean_user_object_2():
    d = datetime.datetime.now() + datetime.timedelta(minutes=30)
    i = d.isoformat()
    t1 = serverly.user.get_new_token(
        "temporary", "read", d)
    t2 = serverly.user.get_new_token("temporary", "write", d)

    n = serverly.utils.clean_user_object([t1, t2])

    a = [{"username": "temporary", "expires": i,
          "scope": "read", "value": t1.value, "id": 1}, {"username": "temporary", "expires": i, "scope": "write", "value": t2.value, "id": 2}
         ]

    for i in a:
        assert i in n


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

    r1 = user._parse_role_hierarchy(e1)
    r2 = user._parse_role_hierarchy(e2)
    r3 = user._parse_role_hierarchy(e3)

    print(r3)

    assert r1 == {"normal": {"normal"}, "admin": {"normal"}}
    assert r2 == {"normal": {"normal"}, "admin": {"normal"}, "staff": {
        "admin", "normal"}, "root": {"admin", "normal", "staff"}, "god": {"admin", "normal", "staff"}}
    assert r3 == {"normal": {"normal"}, "admin": {"normal"},
                  "staff": {"normal"}, "root": {"admin", "normal", "staff"}, "god": {"admin", "normal", "staff", "root"}}


if __name__ == "__main__":
    test_parse_role_hierarchy()
