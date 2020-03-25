"""Implementation of stater allows you to easily create an overview on which servers are currently running"""
import stater as st
import datetime

server_name: str = None
server_password: str = None
component_name: str = None
_errors = []
error_threshold = 60  # minutes


def set(status_code: int):
    if type(status_code) != int:
        raise TypeError("status_code expected to be of type int.")
    if server_name != None and server_password != None and component_name != None:
        st.server_name = server_name
        st.server_password = server_password
        try:
            st.update_component(component_name, status_code)
        except st.ConnectionTimeout:
            raise Warning(
                "Connection timeout to stater server. Cannot update status.")


def setup(servername: str, serverpassword: str, componentname: str, errorthreshold=60):
    """assign all required variabled"""
    global server_name
    global server_password
    global component_name
    global error_threshold
    if type(servername) == str:
        server_name = servername
    else:
        raise TypeError("servername expected to be of type str.")
    if type(serverpassword) == str:
        server_password = serverpassword
    else:
        raise TypeError("serverpassword expected to be of type str.")
    if type(componentname) == str:
        component_name = componentname
    else:
        raise TypeError("componentname expected to be of type str.")
    if type(errorthreshold) == int:
        error_threshold = errorthreshold
    else:
        raise TypeError("errorthreshold expected to be of type str.")


def error():
    global _errors
    global error_treshold
    print(_errors)
    try:
        now = datetime.datetime.now()
        _errors.append(now.isoformat())
        old = datetime.datetime.fromisoformat(_errors[-2])
        new = now - datetime.timedelta(minutes=error_threshold)
        print(new, old)
        if new < old:
            stage = 2
        else:
            stage = 1
    except IndexError:
        stage = 1
    set(stage)
