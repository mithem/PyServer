from serverly.objects import Request, Response


def page_not_found_error(req: Request):
    return Response(404, body=f"<html><h3>404 - Page not found.</h3><br />Sorry, we couldn't find '{req.path.path}'.</html>")


def general_server_error(req):
    return Response(500, body=f"<html><h3>500 - Internal server error.</h3><br />Sorry, something went wrong on our side.")


def user_function_did_not_return_response_object(req):
    return Response(502, body=f"<html><h3>502 - Bad Gateway.</h3><br />Sorry, there is an error with the function serving this site. Please advise the server administrator that the function for '{req.path.path}' is not returning a response object.</html>")
