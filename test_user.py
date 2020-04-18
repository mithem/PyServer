import hashlib

import pytest
import serverly
import serverly.user as user
import sqlalchemy
import os
import warnings

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

    user.setup(filename=FILENAME, user_columns={"first_name": str})

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


@pytest.mark.skip
def test_authenticate():  # TODO whats wrong with this?
    try:
        assert user.authenticate("temporary", "temporary")
        assert not user.authenticate("temporary", "notcorrect")

        assert user.authenticate("temporary", "temporary", True)
    except user.UserNotFoundError:
        pass  # if this test is run seperately, authenticate will not find the user
    with pytest.raises(user.NotAuthorizedError):
        user.authenticate("temporary", "notcorrect")


def test_clean_user_object():
    u = user.User()
    u.id = 0
    u.password = "dnsakjrßheönocuq3öoiewjOurcqwrPOevuiä3u"
    u.salt = "wdaiurjelkcbcjvkerkjwvegröui"
    u.username = "helloworld"
    n = serverly.utils.clean_user_object(u)
    assert getattr(n, "password", None) == None
    assert getattr(n, "salt", None) == None
    c = n.id
    d = n.username
    assert c == 0
    assert d == "helloworld"
