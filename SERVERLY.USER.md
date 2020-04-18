# serverly.user

This subpackage allows very easy user-management right through serverly.

## Table of Contents

- [Configuration](#configuration)
- [ORM (intro)](#orm-intro)
- [Methods](#methods)
  - [setup()](#setup)
  - [register()](#register)
  - [get()](#get)
  - [authenticate()](#authenticate)
  - [get_all()](#get_all)
  - [change()](#change)
  - [delete()](#delete)
- [Standard API](#standard-api)

## Configuration

| Attribute           | Description                                                                                                                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| algorithm: callable | hashlib-like algorithm used for hashing user passwords. If no hashing is intended (VERY INSECURE), you can instead use serverly.user.mockup_hash_algorithm |
| salting: int        | int value of a bool whether to use salting (0 or 1)                                                                                                        |

**Tip:** You can use `serverly.user.setup()` to additionally specify the `filename` of the database (SQLite) and the attributes of the user object (`user_columns`). This is what you want to use for database interactions. It also allows you to tell the SQLite engine to run in `verbose`mode. See [setup()](#setup) for more information.

## ORM (intro)

ObjectRelationalManagers allow you to handle combinations of single values (as found in the database) as objects. Serverly uses [SQLAlchemy](https://www.sqlalchemy.org/) internally.

The standard user is already set up to have an `id`, `username`, `password` and `salt` attribute (even if you disabled salting). You can extend it by specifying `user_columns` in [setup()](#setup)

## Methods

### setup()

This method is used to specify initial configuration options. It accepts the following parameters:

| Parameter                     | Description                                                                                                                                               |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| hash_algorithm: callable      | Algorithm used to hash passwords (and salts if specified). Needs to work like hashlib's: algo(bytes).hexadigest() -> str. Defaults to hashlib's sha3_512. |
| use_salting: bool             | Specify whether to use salting to randomise the hashes of password. Makes it a bit more secure. Defaults to True.                                         |
| filename: str                 |  Filename of the SQLite database                                                                                                                          |
| user_columns: dict[str, type] |  Additional attributes of the user object. See example below. Defaults to an empty dict, meaning the user only has `id`, `username`, `password`, `salt`.  |
| verbose: bool                 | Verbose mode of the SQLite engine                                                                                                                         |

Supported types for `user_columns`' values are str, float, int, bytes, bool.

Example:

```python
user_attrs = {
    'first_name': str,
    'last_name': str,
    'email': str,
    'birth_year': int,
    'gdp': float,
    'newsletter': bool
}

serverly.user.setup(hashlib.sha2_256, use_salting=True, filename='my_database.db', user_columns=user_attrs, verbose=True)
```

### register()

Register a new user. `username` and `password` are obligatory, \*\*kwargs will be used to the corresponding attributes of the User object (defaults to None)

Example (using setup of above):

```python
serverly.user.register('new_user', 'atotallysecurepassword1234', first_name='Tom', email='yo@not10minutemail.com')
```

Raises:

- `UserAlreadyExistsError`

### get()

Get user, authenticated by `username`. If `strict` (default), raise UserNotFoundError if user does not exist. Else return None.

Example:

(_Obviously, this password isn't hashed (& salted)_)

```python
>>> user = serverly.user.get('new_user')
>>> print(user)
<User(id=1, username=new_user, password=atotallysecurepassword1234, salt=..., email=yo@not10minutemail.com, birth_year=None, gdp=None, newsletter=None)>
```

Raises:

- `UserNotFoundError` if `strict`

### authenticate()

Return True or False. Required parameters are `username` and `password`. If `strict`, raise `NotAuthorizedError`.

Examples:

```python
>>>serverly.user.authenticate('new_user', 'atotallysecurepassword1234')
True
>>>serverly.user.authenticate('new_user', 'wrong')
False
>>>serverly.user.authenticate('other_user', 'atotallysecurepassword1234')
Traceback...
UserNotFoundError: 'other_user' not found.
>>>serverly.user.authenticate('new_user', 'atotallysecurepassword1234', strict=True)
True
>>>serverly.user.authenticate('new_user', 'wrong', strict=True)
Traceback...
NotAuthorizedError
```

Raises:

- `UserNotFoundError`
- `NotAuthorizedError` if `strict`

### get_all()

Return a list of all user objects in the database.

Example:

```python
>>> users = serverly.user.get_all()
>>> for user in users:
...     print(user)
<User(id=1, username=new_user, password=atotallysecurepassword1234, salt=..., email=yo@not10minutemail.com, birth_year=None, gdp=None, newsletter=None)>
```

### change()

Change user with current username `username`. Accepted parameters are `new_username`, `password` (new) and `**kwargs`. `**kwargs` will change the user attributes defined in the keys to those values.

Example:

```python
>>> serverly.user.change('new_user', birth_year=1970, gdp=42943.9, newsletter=False)
>>> print(serverly.user.get('new_user'))
<User(id=1, username=new_user, password=atotallysecurepassword1234, salt=..., email=yo@not10minutemail.com, birth_year=1970, gdp=42943.9, newsletter=False)>
```

Raises:

- `UserNotFoundError`

### delete()

Delete a user permanently and non-revokable. `username` required.

Example:

```python
>>> serverly.user.delete('new_user')
>>> serverly.user.get('new_user')
None
```

Raises:

- `UserNotFoundError`.

## Standard API

Serverly comes with a builtin standard API for user management. You just have to tell it where your endpoint should go.

To use it, just call the `use`-method and specify `function: str`, `method: str` and `path: str`. You of course have to `import serverly.user.api`. The following functions (of user-management) are supported:

- authenticate
- change
- delete
- get
- register

Example:

```python
>>> serverly.user.api.use('register', 'POST', '/api/register')
```

Voilà, serverly now listens on the POST endpoint 'api/register'!

Documententation of the standard API, what it accepts, what it returns, etc. is available on [Postman](https://documenter.getpostman.com/view/10720102/Szf549XF?version=latest)
