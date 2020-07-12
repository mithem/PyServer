class NotAuthorizedError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class MissingParameterError(Exception):
    pass


class ConfigurationError(Exception):
    pass


class UnsupportedHTTPMethod(Exception):
    pass


class _BrakeException(Exception):
    pass
