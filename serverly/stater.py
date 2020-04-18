"""Implementation of stater allows you to easily create an overview on which servers are currently running"""
try:
    import stater as st
except ImportError:
    raise Exception(
        "module 'stater' is needed to communicate with the stater server. It's available on PyPi as 'stater'")
import datetime

server_name: str = None
server_password: str = None
component_name: str = None
_errors = []
error_threshold = 60  # minutes


def set(status_code: int):
    """

    :param status_code: int: new status code

    """
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
        except Exception as e:
            raise Warning(
                f"[{type(e).__name__}] Error while updating the status of the stater server: " + str(e))


def setup(servername: str, serverpassword: str, componentname: str, errorthreshold=60):
    """assign all required variables

    :param servername: str: name of the server (in stater)
    :param serverpassword: str: password of the server (in stater)
    :param componentname: str: name of the component (this server) in stater
    :param errorthreshold: amount of minutes in which multiple calls of error() will trigger stater to mark this server/component as failed(Default value = 60)
    """
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


def error(logger):
    """

    :param logger: logger to log any exceptions to

    """
    global _errors
    global error_treshold
    try:
        now = datetime.datetime.now()
        _errors.append(now.isoformat())
        old = datetime.datetime.fromisoformat(_errors[-2])
        new = now - datetime.timedelta(minutes=error_threshold)
        if new < old:
            stage = 2
        else:
            stage = 1
    except IndexError:
        stage = 1
    try:
        set(stage)
    except Exception as e:
        logger.handle_exception(e)
