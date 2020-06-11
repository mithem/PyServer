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
- [MailManager](#mailmanager)
  - [Configuration](#mailmanager-configuration)
  - [Methods](#mailmanager-methods)
- [Sessions](#sessions)
- [Auth](#auth)
  - [basic_auth()](#basic_auth)
  - [bearer_auth()](#bearer_auth)
  - [session_auth()](#session_auth)
- [Role-based Authorization](#role-based-authorization)

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

| Parameter                     | Description                                                                                                                                                                                                                                    |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| hash_algorithm: callable      | Algorithm used to hash passwords (and salts if specified). Needs to work like hashlib's: algo(bytes).hexadigest() -> str. Defaults to hashlib's sha3_512.                                                                                      |
| use_salting: bool             | Specify whether to use salting to randomise the hashes of password. Makes it a bit more secure. Defaults to True.                                                                                                                              |
| filename: str                 |  Filename of the SQLite database                                                                                                                                                                                                               |
| user_columns: dict[str, type] |  Additional attributes of the user object. See example below. Defaults to an empty dict, meaning the user only has `id`, `username`, `password`, `salt`.                                                                                       |
| verbose: bool                 | Verbose mode of the SQLite engine                                                                                                                                                                                                              |
| require_email_verification    |  Require that the email of the user is verified when authenticating. Has no effect on the `authenticate`-method but on the `basic_auth`-decorator for example.                                                                                 |
| role_hierarchy                |  A dictionary with roles as keys & values. If an endpoint requires a role the user does not have explicitly, the user will be authorized if his 'subroles' match de required one(s). See [role-based authorization](#role-based-authorization) |

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

### get_by_email()

Get user specified by `email`. If `strict` (default), raise UserNotFoundError if user does not exist. Else return None.

Example:

```python
>>> user = serverly.user.get_by_email('yo@not10minutemail.com')
>>> print(user)
<User(id=1, username=new_user, password=atotallysecurepassword1234, salt=..., email=yo@not10minutemail.com, birth_year=None, gdp=None, newsletter=None)>
```

Raises:

- `UserNotFoundError` if `strict`

### get_by_token()

Get user specified by `bearer_token`. If `strict` (default), raise UserNotFoundError if no one is found. Else return None.

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

### delete_all()

Delete all users in the database permanently.

## Standard API

Serverly comes with a builtin standard API for user management. You just have to tell it where your endpoint should go.

To use it, just call the `use`-method and specify `function: str`, `method: str` and `path: str`. You of course have to `import serverly.user.api`. The following functions (of user-management) are supported (and many more, see docstrings):

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

Also, if you have a Mac (or Hackintosh) and an iOS / iPadOS device, you can check out the following repo for an app that offers a basic UI for the /console (overview) page.

## MailManager

The MailManager (`serverly.user.mail.manager`) allows you to send emails (automatically as well as manually). It only supports **gmail** and you need to enable 'access by less secure app' as serverly does using `yagmail` (you need that too) with OAuth. Using the functions in this module requires that the User object has the attributes `username` (obviously) `email` and `verified`.

You can easily set up the manager (there isn't really a good other way) by calling

```python
serverly.user.mail.setup(
    email_address: str,
    email_password: str,
    verification_subject_template: str=None,
    verification_content_template: str=None,
    online_url="",
    pending_interval=15,
    scheduled_interval=15,
    debug=False
)
```

### MailManager Configuration

| Attribute               | Description                                                                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| email_address: str      | Your gmail address                                                                                                                                                                                            |
| email_password: str     | Your gmail (google) password (No config file for that one 😉; You shall implement that yourself)                                                                                                              |
| special_mails: dict     | special email templates used for mails like password reset or mail verification. See [special mails](#special-mails) for more information.                                                                    |
| online_url: str         | URL where the server can be reached (`superpath` **not** included). Will be used to replace `$verification_url` when using `schedule_verification_mail()` and/or the [register() standard api](#standard-api) |
| pending_interval: int   |  Interval (seconds) pending (non-scheduled) emails will be tried to send                                                                                                                                      |
| scheduled_interval: int |  Interval (seconds) scheduled mails will be sent if they should (see [schedule()](#schedule))                                                                                                                 |
| debug: bool             | debug/verbose mode                                                                                                                                                                                            |

### Special mails

You can specify special mail templates in `serverly.user.mail._default_special_emails` or preferably by calling setup and passing `special_mails`. The default is the following:

```python
{
    "verification": {
        "subject": "Your recent registration",
        "content": f"Hey $username,\nthank you for signing up for our service. Please click <a href='$verification'>this link</a> to verify your email.\n\nIf you cannot click the link for some reason, you can also just copy/paste it: \n$verification"
    },
    "confirmation": {
        "subject": "Please verify your email",
        "content": f"Hey $username,\nwe'd appreciate if you could verify your email by clicking <a href='$confirmation'>this link</a>, just in case!\n\nIf you cannot click the link for some reason, you can also just copy/paste it: \n$confirmation"
    },
    "password_reset": {
        "subject": "You lost your password?",
        "content": "Hi $username,\nit looks like you recently requested to change your password. You can use <a href='$password_reset'>this link</a> to reset it.\n\nTip: If you cannot the link above, try copy/pasting it in your browser: $password_reset\n\nAnother one: If you didn't request this, you can just delete this email."
    }
}
```

In each value (both subject and content), you can use placeholders which will be substituted with the users' attributes as well as other special strings. These are equal to the special email type (e.g. `verification`, `password_reset`) and are substituted by the unique url generated for the particular action.

### MailManager Methods

| Method                                       | Description                                                                                                                                                                                                                                                      |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| schedule(email={}, immediately=True)         | Schedule a new email: dict. 'email' or 'username' as well as 'subject' are required. Use 'schedule': Union[isoformat, datetime.datetime] to schedule it for some time in the future. Required if 'immediately' is False. If 'immediately' is True, send it ASAP. |
| send_pending()                               |  Usually not needed, but you can call this to send them manually.                                                                                                                                                                                                |
| send_scheduled()                             |  Same as above                                                                                                                                                                                                                                                   |
| start()                                      | Start the manager. If everything goes right, this will already be done by serverly, so you would just create another worker. I don't think that this would increase the server's capacity though as each mail is sent in another process either way.             |
| schedule_verification_mail(username:str)     | Schedule a verification mail to user specified. Will use `verification_subject` and `verification_template` as a, well, template...                                                                                                                              |
| schedule_password_reset_email(username: str) |  Schedule a password reset mail to user specified                                                                                                                                                                                                                |
| verify()                                     | Verify user.                                                                                                                                                                                                                                                     |

## Sessions

Sessions allow you to keep track of user activity. Use can use the [standard API](#standard-api) to serve useful endpoints.

### Session configuration

| Attribute                    | Description                                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------------------------- |
| session_renew_threshold = 60 | number of seconds after which a new session will be created instead of increasing the end date |

### Session attributes

| Attribute                              | Description                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| id: int                                | id                                                           |
| username: str                          | username session belongs to                                  |
| start: datetime.datetime               | start date of the session                                    |
| end: datetime.datetime                 | end date of the session                                      |
| address: str                           | str representation of user's address (i.e. 'localhost:5678') |
| length: datetime.timedelta (read-only) | length of the session                                        |

### Methods for sessions

All of these are located in `serverly.user`

| Method                                         | Description                                                                                                                                                      |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| get_all_sessions(username: str)                | Return all sessions for `username`. `username`=None -> Return all sessions of all users.                                                                         |
| get_last_session(username: str)                | Return last session object for `username`. None if no session exists.                                                                                            |
| extend_session(id, new_end: datetime.datetime) | extend existint session up to new_end                                                                                                                            |
| new_activity(username: str, address: tuple)    | Update sessions to reflect a new user activity. If previous' sessions' (?) 'distance' is under `session_renew-treshold`, extend the last one, else create a new. |
| delete_sessions(username: str)                 | Delete all sessions of `username`. Set to None to delete all sessions. Non-revokable.                                                                            |

## Auth

Serverly comes with built-in decorators for HTTP Basic & Bearer authentication. When authentication successful, the user will automatically be fetched from the database and be assigned to request.user. If the authentication fails, serverly will respond with the appropriate code and message. Also see [customization](#customization).

### basic_auth()

Authenticate with a username and password. **Insecure on non-HTTPS-Connections** (which serverly **does not** provide)!

Example:

```python
@serves('GET', '/secret')
@user.basic_auth
def my_page(req):
    return Response(body=f"You're logged in as {req.user.username}!")
```

Note: authorization decorators need to be placed 'under' / 'after' the serves-decorator.

### bearer_auth()

Authenticate via Bearer token. To map tokens to users and vice-versa, each user needs to have an attribute `bearer-token`. You can change it by just calling user.change(bearer_token=...) or using the standard API (bearer.new)
You can specify that your function requires the user to have an specific scope (or higher of course). `scope` can be of type str or list\<str\>.

`expired: bool` specifies whether to handle expired tokens appropriately (-> not authorized).

Example:

```python
@serves('GET', '/bearer')
@user.bearer_auth('admin')
def my_page(req):
    return Response(body=f"You authenticated as {req.user.username}! Also, you're an admin! 🎉")
```

### session_auth()

Special authorization using Bearer tokens (see [bearer_auth()](#bearer_auth); therefore same requirements and token generation). Uses sessions and `session_renew_treshold` to decide whether to log in a user (assuming their bearer token is valid). If the last session of the user, which means that they where authenticated then is less than `session_renew_treshold` in the past, they are authorized.

Example:

```python
@serves('GET', '/newproduct')
@user.session_auth
def my_page(req):
    return Response(body=f'You authenticated as {req.user.username} with bearer token {req.user.bearer_token}!')
```

### Customization

Serverly offers 3 templates (the string library's template engine) for how to respond to which falsy request.

| Status code        | Varname              | Default       | Available variables                                                | Example                 |
| ------------------ | -------------------- | ------------- | ------------------------------------------------------------------ | ----------------------- |
| 404 - Not found    | USER_NOT_FOUND_TMPLT |  User \$e     | user attributes, e: str(Exception)                                 | User 'hello' not found. |
| 401 - Unauthorized | UNAUTHORIZED_TMPLT   | Unauthorized. | user attributes, e: str(Exception) when using basic authentication |

## Role-based Authorization

Serverly also comes with a built-in role-based authorization. This means that you can assign custom roles as strings to users and authenticate them in certain endpoints based on the fact whether they are assigned a certain role.

You can define which roles should be allowed for any endpoint by using the `serverly.user.requires_role(role: Union[str, list])`-decorator where role is a str or list of strings which should be allowed in the endpoint.

The user object needs to have a `role` attribute.

Example:

```python
@serves('GET', '/status')
@user.basic_auth
@user.requires_role('admin')
def admin_status_page(req):
    return Response(body=f"Everything fine!")
```

You can set up a role hierarchy in setup() with a dictionary with roles as keys & values. If an endpoint requires a role the user does not have explicitly, the user will be authorized if his 'subroles' match de required one(s).

Example for the `role_hierarchy`-parameter:

```python
{
    'normal': 'normal', # required
    'admin': 'normal',
    'staff': 'normal'
    'root': 'admin'
}
```

Then, admins & staff have the same rights as normals, root has the same as admin & staff (and therefore normals).
