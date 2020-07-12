import serverly
from serverly.objects import Response


class Plugin:

    def use(self):
        _plugin_manager.use(self)


class ServerLifespanPlugin(Plugin):
    def onServerStart(self):
        raise NotImplementedError()

    def onServerShutdown(self):
        raise NotImplementedError()


class HeaderPlugin(Plugin):

    description = "A plugin designed to manipulate the headers of every response"

    def __init__(self, exceptions=[]):
        self.exceptions = exceptions

    def manipulateHeaders(self, response: Response) -> Response:
        raise NotImplementedError()


class ContentSecurityPolicyHeaderPlugin(HeaderPlugin):

    def __init__(self, policy: str, exceptions=[]):
        super().__init__(exceptions)
        self.policy = policy

    def manipulateHeaders(self, response: Response) -> Response:
        response.headers["content-security-policy"] = self.policy
        return response


class X_Frame_OptionsHeaderPlugin(HeaderPlugin):

    def __init__(self, policy: str, exceptions=[]):
        super().__init__(exceptions)
        self.policy = policy

    def manipulateHeaders(self, response: Response) -> Response:
        response.headers["x-frame-options"] = self.policy
        return response


class X_Content_TypeOptionsHeaderPlugin(HeaderPlugin):

    def __init__(self, policy: str, exceptions=[]):
        super().__init__(exceptions)
        self.policy = policy

    def manipulateHeaders(self, response: Response) -> Response:
        response.headers["x-content-type-options"] = self.policy
        return response


class _PluginManager:
    def __init__(self):
        self.plugins = []
        self.server_lifespan_plugins = []
        self.header_plugins = []

    def use(self, plugin: Plugin):
        if issubclass(plugin.__class__, HeaderPlugin):
            l = self.header_plugins
        elif issubclass(plugin.__class__, ServerLifespanPlugin):
            l = self.server_lifespan_plugins
        else:
            l = self.plugins

        for p in l:
            if plugin.__class__.__name__ == p.__class__.__name__:
                return

        l.append(plugin)


_plugin_manager = _PluginManager()
