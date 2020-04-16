# serverly

A wrapper-kindof-thing that makes using servers in Python severly easier.

IMPORTANT NOTE for v0.2.0: This update removed backwards-compability for functions written for previous versions of serverly. You now NEED to return a response object.

## decorators

```python
@serves("POST", "/newmessage")
def new_message(req: serverly.Request):
    with open("messages.txt", "a+") as f:
        f.write(req.body + "\n")
```
