import pytest

import serverly
from serverly import plugins
from serverly.objects import Response


def test_plugin_manager():
    class MockPlugin(plugins.Plugin):
        pass

    class HeaderPlugin(plugins.HeaderPlugin):
        pass

    class AnotherHeaderPlugin(plugins.HeaderPlugin):
        pass

    class LifespanPlugin(plugins.ServerLifespanPlugin):
        pass

    assert plugins._plugin_manager.plugins == []
    MockPlugin().use()
    assert len(plugins._plugin_manager.plugins) == 1

    assert plugins._plugin_manager.header_plugins == []
    HeaderPlugin().use()
    assert len(plugins._plugin_manager.header_plugins) == 1

    AnotherHeaderPlugin().use()
    assert len(plugins._plugin_manager.header_plugins) == 2

    assert plugins._plugin_manager.server_lifespan_plugins == []
    LifespanPlugin().use()
    assert len(plugins._plugin_manager.server_lifespan_plugins) == 1

    LifespanPlugin().use()
    assert len(plugins._plugin_manager.server_lifespan_plugins) == 1


def test_HeaderPlugin():
    with pytest.raises(NotImplementedError):
        plugins.HeaderPlugin().manipulateHeaders(Response())


def test_csp_header_plugin():
    assert plugins.Content_Security_PolicyHeaderPlugin("my policy").manipulateHeaders(
        Response()).headers["content-security-policy"] == "my policy"


def test_xfo_header_plugin():
    assert plugins.X_Frame_OptionsHeaderPlugin("my other policy").manipulateHeaders(
        Response()).headers["x-frame-options"] == "my other policy"


def test_xcto_header_plugin():
    assert plugins.X_Content_TypeOptionsHeaderPlugin("Another policy").manipulateHeaders(
        Response()).headers["x-content-type-options"] == "Another policy"


def test_server_lifespan_plugin():
    with pytest.raises(NotImplementedError):
        plugins.ServerLifespanPlugin().onServerStart()

    with pytest.raises(NotImplementedError):
        plugins.ServerLifespanPlugin().onServerShutdown()
