# serverly - http.server wrapper and helper

A really simple-to-use HTTP-server!

## Configuration
`address = ('localhost', 8080)` The address used to register the server. Needs to be set before running start()

`name = 'serverly'` The name of the server. Used for logging purposes only.

`logger: fileloghelper.Logger = Logger()` The logger used for logging (surprise!!). See the docs of fileloghelper for reference.

## Custom (dynamic) functions

When you create custom functions you need to tell serverly by either using the `serves(method: str, path: str)` decorator or register it by calling `register_function` (see below). Your function should accept one parameter which is of type Request. You can then process it in whatever way you want.
Your function must return a Response object. See Objects for more info.

## Methods
`static_page(file_path: str, path: str)`
Register a static page where the file is located under `file_path` and will serve `path`

`register_function(method: str, path: str, function)` 
Register a dynamic function that will serve `path` via `method`

`unregister(method: str, path: str)`
Unregister any page (static or dynamic). Only affect the `method`-path (GET / POST)

`start(superpath: str='/')`
Start the server after applying all relevant attributes like address. `superpath` will replace every occurence of SUPERPATH/ or /SUPERPATH/ with `superpath`. Especially useful for servers orchestrating other servers.

`register_error_response(code: int, msg_base: str, mode='enumerate')`
Register an error response template for `code` based off the message-stem `msg_base`and accepting *args as defined by `mode`

`error_template(code: int, *args)`

#### Modes

- enumerate: append every arg by comma and space to the base
- base: only return the base message
    
#### Example

```python
register_error_response(404, 'Page not found.', 'base')
```
You can now get the 404-Response by calling `error_response(404)` -> Response(code=404, body='Page not found.')

Or in enumerate mode:

```python
register_error_response(999, 'I want to buy: ', 'enumerate')
```

`error_response(999, 'apples', 'pineapples', 'bananas')` -> Response(code=9l9, body='I want to buy: apples, pineapples, bananas')

`error_response(code: int, *args)`
Return Response registered by register_error_response (See above)

## Objects

### Request
<!--- TODO: check if address really looks like this!-->
Attribute | Description
-|-
method: str | HTTP method (GET, POST, PUT, DELETE)
path: str | Path the request was sent to (e.g. /projects/doorbell)
address: tuple[str, int] | Address of client as a tuple, e.g. ("localhost": 65732)
authenticated: bool | Is user authenticated using the Authorization-Header?
auth_type: str | Type of authorization (Authorization-Header). Currently Basic & Bearer supported.
user_cred: Union[str, tuple[str, str]] | Credentials of the user passed in the Authorization-Header. If `auth_type` is Basic, `user_cred` is a tuple containing username & password. The password is already decrypted from base64. If `auth_type` is Bearer, `user_cred` is the bearer token (str).

### Response

Attribute | Description
- | -
code: int | Response code to send to the client

### Both (Request & Response)

Attribute | Description
- | -
headers: dict | Headers as a dict[str, Union[str, int]] recieved by the client or yet to return to it
(set) body: Union[str, dict, list] | set `body` to a str, dict or list. Translating it into JSON, if necessary is handled automatically
(get) body: str | get the JSON representation of the request/response if available, otherwise just the string.
(get) obj: object | get the object representation of the request/response. If there is none (body is a non-JSON string for example) it is set to None. NOT SET-able.

Due to the properties above the probably best way to use requests/responses is by assigning values like dictionaries to the body attribute of responses and accessing the json of requests by using body (i.e. to store it in a database)
