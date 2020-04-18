from functools import wraps
import json
import string


if __name__ != "__main__":
    import serverly
    from serverly.utils import ranstr
try:
    import yagmail
    yag = None
    mail_avail = True
except ImportError as e:
    mail_avail = False
    try:
        raise ImportError(
            "Module 'yagmail' cannot be importet. You cannot use serverly.user.mail.")
    except ImportError as e:
        serverly.logger.handle_exception(e)
except Exception as e:
    mail_avail = False
    serverly.logger.handle_exception(e)

_VERIFICATION_SUBJECT = "Your recent registration"
_VERIFICATION_TEMPLATE = """Hey $username,
You recently signed up for our service. Please click the <a href="$verification_url">this link</a> to verify your email 😊.
(In case you cannot click the link above, you can also copy/paste it: $verification_url)
"""


email_address = None
account_password = None
verification_subject = None
verification_template = None


def _setup_complete():
    return yag != None and mail_avail == True and email_address != None and account_password != None


def setup(email: str = None, password: str = None, email_verification_subject=None, email_verification_template=None):
    global yag, email_address, account_password, verification_subject, verification_template
    email_address = email
    account_password = password
    if email_verification_subject == None:
        verification_subject = _VERIFICATION_SUBJECT
    else:
        verification_subject = email_verification_subject
    if email_verification_template == None:
        verification_template = _VERIFICATION_TEMPLATE
    else:
        verification_template = email_verification_template
    yag = yagmail.SMTP(email_address, password)


def _full_setup_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _setup_complete():
            return func(*args, **kwargs)
        try:
            raise UserWarning(
                "Mail client (gmail) not set up. Use serverly.user.mail.setup() to do.")
        except Exception as e:
            serverly.logger.handle_exception(e)
    return wrapper


def verify(username: str):
    serverly.user.change(username, verified=True)
    serverly.logger.success(f"verified email of {username}!")


@_full_setup_required
def send_verification_mail_to(username: str):
    try:
        identifier = ranstr()
        verification_url = "/SUPERPATH/verify/" + identifier
        substitutions = {**serverly.user.get(username).to_dict(),
                         **{"verification_url": verification_url}}
        for key, value in substitutions.items():
            substitutions[key] = str(value)

        subject_temp = string.Template(verification_subject)
        content_temp = string.Template(verification_template)

        subject = subject_temp.substitute(substitutions)
        content = content_temp.substitute(substitutions)

        try:
            send(username, subject, content)
            try:
                with open("pending_verifications.json", "r") as f:
                    try:
                        data = json.load(f)
                    except:
                        data = {}
            except FileNotFoundError:
                with open("pending_verifications.json", "w+") as f:
                    data = {}
                    f.write("{}")
            data[identifier] = username
            with open("pending_verifications.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            serverly.logger.handle_exception(e)
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


def get_email_from_username(username: str):
    user = serverly.user.get(username)
    return str(user.email)


@_full_setup_required
def send(username: str, subject: str, message="", attachments=None):
    try:
        email = get_email_from_username(username)
        yag.send(to=email, subject=str(subject),
                 contents=str(message), attachments=attachments)
        serverly.logger.success(f"Sent mail to {username} ({email}).")
    except Exception as e:
        serverly.logger.handle_exception(e)
