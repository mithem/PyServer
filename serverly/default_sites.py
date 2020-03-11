def page_not_found_error(data):
    return {"Content-type": "text/plain", "response_code": 404}, "404 - Page not found"


def general_server_error(data):
    return {"Content-type": "text/plain", "response_code": 500}, "500 - Internal server error"
