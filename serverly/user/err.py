class NotAuthenticatedError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class MissingParameterError(Exception):
    pass
