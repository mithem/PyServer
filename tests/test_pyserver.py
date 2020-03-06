import pytest
from serverly import Server


def test_get_server_address():
    valid = ("localhost", 8080)
    assert Server._get_server_address(
        ("localhost", 8080)) == valid
    assert Server._get_server_address("localhost,8080") == valid
    assert Server._get_server_address("localhost, 8080") == valid
    assert Server._get_server_address("localhost;8080") == valid
    assert Server._get_server_address("localhost; 8080") == valid


def test_get_server_address_2():
    valid = ("localhost", 8080)
    with pytest.raises(Exception):
        with pytest.warns(UserWarning, match="bostname and port are in the wrong order. Ideally, the addresses is a tuple[str, int]."):
            Server._get_server_address((8080, "local#ost"))
