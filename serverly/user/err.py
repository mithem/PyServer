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
