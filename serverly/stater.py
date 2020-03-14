"""Implementation of stater allows you to easily create an overview on which servers are currently running"""
import stater as st

server_name: str = None
server_password: str = None
component_name: str = None


def set(status_code: int):
    if type(status_code) != int:
        raise TypeError("status_code expected to be of type int.")
    if server_name != None and server_password != None and component_name != None:
        st.server_name = server_name
        st.server_password = server_password
        st.update_component(component_name, status_code)


def setup(servername: str, serverpassword: str, componentname: str):
    """assign all required variabled"""
    global server_name
    global server_password
    global component_name
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
