import datetime
import json
import multiprocessing
import re
import string
import time
from functools import wraps

import serverly
import serverly.user
import yagmail
from serverly.user import _requires_user_attr
from serverly.utils import ranstr

_default_special_emails = {
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


class MailManager:
    @_requires_user_attr("email")
    def __init__(self, email_address: str, email_password: str, special_emails={}, online_url: str = "", pending_interval=15, scheduled_interval=15, debug=False):
        """
        :param email_address: (g)mail address to send emails from
        :param email_password: gmail password (requires 'less secure apps')
        :param special_emails: dict of dicts specifying how some emails look like. Supports the following:
        - verification
        - password_reset

        Example:
        ```
        {
            'verification': {
                'subject': '${username}'s registration',
                'content': 'Hi $username,\nYou recently registered. Click this link to verify: $verification_url'
            }
        }
        ```
        :param online_url: url the server is available at. Used for giving users the full link.
        :param pending_interval: interval (seconds) pending emails will be sent.
        :param scheduled_interval: interval (seconds) scheduled emails will be sent (if scheduled of course).
        :param debug: debug mode; more verbosity
        """
        self._email_address = None
        self._email_password = None
        self._special_emails = None
        self._online_url = None

        self.email_address = email_address
        self.email_password = email_password
        self.special_emails = special_emails
        self.online_url = online_url

        self.pending = []
        self.scheduled = []

        self.pending_interval = int(pending_interval)
        self.scheduled_interval = int(scheduled_interval)

        self.debug = debug

    def _renew_yagmail_smtp(self):
        self.yag = yagmail.SMTP(self.email_address, self.email_password)

    @property
    def email_address(self):
        return self._email_address

    @email_address.setter
    def email_address(self, new_email):
        email_pattern = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if not re.match(email_pattern, str(new_email)):
            raise ValueError("Email appears to be invalid.")
        self._email_address = str(new_email)
        self._renew_yagmail_smtp()

    @property
    def email_password(self):
        return self._email_password

    @email_password.setter
    def email_password(self, new_password):
        self._email_password = str(new_password)
        self._renew_yagmail_smtp()

    @property
    def special_emails(self):
        """For docstrings, see MailManager.__init__()"""
        return self._special_emails

    @special_emails.setter
    def special_emails(self, special_emails: dict):
        """For docstrings, see MailManager.__init__()"""
        try:
            self._special_emails = {**_default_special_emails,
                                    **self.special_emails, **special_emails}
        except TypeError:  # there must be a better way 🤔
            try:
                self._special_emails = {
                    **_default_special_emails, **self.special_emails}
            except TypeError:
                self._special_emails = _default_special_emails

    @property
    def online_url(self):
        return self._online_url

    @online_url.setter
    def online_url(self, online_url: str):
        url_pattern = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~# =]{1,256}(\.|:)[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        if not re.match(url_pattern, str(online_url)) and not online_url == "":
            raise ValueError("Online_url appears to be invalid.")
        self._online_url = str(online_url)

    def send(self, subject: str, content="", attachments=None, username: str = None, email: str = None, substitute=False):
        """send email immediately and without multiprocessing. If `substitue`, substitute user attributes with the string library's template engine."""
        try:
            if username != None:
                user = serverly.user.get(str(username))
            elif email == None:
                return serverly.logger.warning("Cannot send email: Neither username nor email provided.", extra_context="MailManager")
            else:
                if substitute:
                    user = serverly.user.get_by_email(email)
            if substitute:
                subject_temp = string.Template(subject)
                content_temp = string.Template(content)

                d = user.to_dict()

                subject = subject_temp.safe_substitute(**d)
                content = content_temp.safe_substitute(**d)

            self.yag.send(email, subject, content, attachments)
            if self.debug:
                serverly.logger.success(
                    f"Sent mail to {email if email != None else user.email}!")
        except KeyboardInterrupt:
            pass
        except Exception as e:
            serverly.logger.handle_exception(e)
            raise e

    def schedule(self, email={}, immediately=True):
        """schedule a new email: dict. 'email' or 'username' as well as 'subject' are required. Use 'schedule': Union[isoformat, datetime.datetime] to schedule it for some time in the future. Required if 'immediately' is False. If 'immediately' is True, send it ASAP."""
        try:
            if email.get("email", email.get("mail", None)) == None:
                if serverly.user.get(email["username"]).email == None:
                    return False
            self._load()
            if immediately:
                self.pending.append(email)
            else:
                if type(email["schedule"]) == str:
                    email["schedule"] = datetime.datetime.fromisoformat(
                        email["schedule"])
                elif type(email["schedule"]) != datetime.datetime:
                    raise TypeError(
                        "email['schedule'] not an isoformat str or datetime.datetime object")
                self.scheduled.append(email)
            self._save()
        except Exception as e:
            serverly.logger.handle_exception(e)

    def _load(self):
        """load latest mails into self.pending and self.scheduled"""
        try:
            with open("mails.json", "r") as f:
                data = json.load(f)
            for obj in data["scheduled"]:
                obj["schedule"] = datetime.datetime.fromisoformat(
                    obj["schedule"])
            self.pending = data["pending"]
            self.scheduled = data["scheduled"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
            self.pending = []
            self.scheduled = []
            self._save()

    def _save(self):
        try:
            scheduled = []
            for mail in self.scheduled:
                new = mail.copy()
                new["schedule"] = mail["schedule"].isoformat()
                scheduled.append(new)

            with open("mails.json", "w+") as f:
                json.dump({"pending": self.pending,
                           "scheduled": scheduled}, f)
        except Exception as e:
            serverly.logger.handle_exception(e)

    def send_pending(self):
        try:
            self._load()
            processes = []
            for mail in self.pending:
                def send():
                    try:
                        self.send(mail["subject"], mail.get("content", ""),
                                  mail.get("attachments", None), mail.get("username", None), mail.get("email", None), mail.get("substitute", True))
                        self.pending.pop(self.pending.index(mail))
                        self._save()
                    except KeyboardInterrupt:
                        self._save()
                processes.append(multiprocessing.Process(
                    target=send, name="Sending of email"))
            for process in processes:
                process.start()
            for process in processes:
                process.join()
            return len(processes)
        except KeyboardInterrupt:
            self._save()
        except Exception as e:
            self._save()
            raise e

    def send_scheduled(self):
        try:
            self._load()
            processes = []
            for mail in self.scheduled:
                def send():
                    try:
                        self.send(mail["subject"], mail.get("content", ""),
                                  mail.get("attachments", None), mail.get("username", None), mail.get("email", None))
                        self.scheduled.pop(self.scheduled.index(mail))
                        self._save()
                    except KeyboardInterrupt:
                        self._save()
                if datetime.datetime.now() >= mail["schedule"]:
                    processes.append(multiprocessing.Process(target=send))
            for process in processes:
                process.start()
            for process in processes:
                process.join()
            return len(processes)
        except KeyboardInterrupt:
            self._save()
        except Exception as e:
            self._save()
            raise e

    def start(self):
        def pending():
            try:
                while True:
                    n = self.send_pending()
                    serverly.logger.context = "MailManager"
                    serverly.logger.success(
                        f"Sent {str(n)} pending emails", self.debug)
                    time.sleep(self.pending_interval)
            except KeyboardInterrupt:
                self._save()
            except Exception as e:
                serverly.logger.handle_exception(e)

        def scheduled():
            try:
                while True:
                    n = self.send_scheduled()
                    serverly.logger.context = "MailManager"
                    serverly.logger.success(
                        f"Sent {str(n)} scheduled emails", self.debug)
                    time.sleep(self.scheduled_interval)
            except KeyboardInterrupt:
                self._save()
            except Exception as e:
                serverly.logger.handle_exception(e)

        self._load()

        pending_handler = multiprocessing.Process(
            target=pending, name="MailManager: Pending")
        scheduled_handler = multiprocessing.Process(
            target=scheduled, name="MailManager: Scheduled")

        pending_handler.start()
        scheduled_handler.start()

        serverly.logger.context = "startup"
        serverly.logger.success("MailManager started!")

    def get_substituted_mail(self, type_: str, **substitutions):
        """:param type: email type as a key in MailManager.special_emails, e.g. 'verification'

        Raises KeyError if type is not defined."""
        try:
            mail = self.special_emails[type_].copy()
            mail["subject"] = string.Template(
                mail["subject"]).safe_substitute(**substitutions)
            mail["content"] = string.Template(
                mail["content"]).safe_substitute(**substitutions)
            return mail
        except TypeError:
            raise KeyError(f"mailtype (got {type_})")

    def _identifier_based_special_mail(self, email_type: str, username: str, path: str):
        def get_func_path(path: str):
            path = path[1:] if path[0] == "/" else path
            path = path + "/" if path[-1] != "/" else path
            return path
        try:
            identifier = ranstr()
            url = self.online_url + \
                serverly._sitemap.superpath + \
                get_func_path(path) + identifier
            subs = {}
            for k in self.special_emails.keys():
                subs[k] = url
            mail = self.get_substituted_mail(
                email_type, **serverly.user.get(username).to_dict(), **subs)
            mail["username"] = username
            b = self.schedule(mail)
            if not b:
                return False
            try:
                with open("mailmanager.json", "r") as f:
                    try:
                        data = json.load(f)
                    except:
                        data = {}
            except FileNotFoundError:
                with open("mailmanager.json", "w+") as f:
                    data = {"verification": {},
                            'password_reset': {},
                            "confirmation": {}
                            }
                    json.dump(data, f)
            data[email_type][identifier] = username
            with open("mailmanager.json", "w") as f:
                json.dump(data, f)
            return True
        except Exception as e:
            serverly.logger.handle_exception(e)
            raise e

    def schedule_verification_mail(self, username: str):
        return self._identifier_based_special_mail(
            "verification", username, "verify/")

    def schedule_confirmation_mail(self, username: str):
        return self._identifier_based_special_mail(
            "confirmation", username, "confirm/")

    def schedule_password_reset_mail(self, username: str):
        return self._identifier_based_special_mail(
            "password_reset", username, "reset-password/")


@_requires_user_attr("verified")
def verify(identifier: str):
    try:
        with open("mailmanager.json", "r") as f:
            data = json.load(f)
        for identi, username in data["verification"].items():
            if identi == identifier:
                serverly.user.change(username, verified=True)
                del data["verification"][identifier]
                with open("mailmanager.json", "w") as f:
                    json.dump(data, f)
                serverly.logger.success(f"verified email of {username}!")
                return True
        return False
    except (FileNotFoundError, json.JSONDecodeError):
        _set_up_mailmanager_json()
        verify(identifier)
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


@_requires_user_attr("verified")
def confirm(identifier: str):
    try:
        with open("mailmanager.json", "r") as f:
            data = json.load(f)
        for identi, username in data["confirmation"].items():
            if identi == identifier:
                serverly.user.change(username, verified=True)
                del data["confirmation"][identifier]
                with open("mailmanager.json", "w") as f:
                    json.dump(data, f)
                serverly.logger.success(f"confirmed email of {username}!")
                return True
        return False
    except (FileNotFoundError, json.JSONDecodeError):
        _set_up_mailmanager_json()
        confirm(identifier)
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


def reset_password(identifier: str, password: str):
    try:
        with open("mailmanager.json", "r") as f:
            data = json.load(f)
        for identi, username in data["password_reset"].items():
            if identi == identifier:
                serverly.user.change(username, password=password)
                del data["password_reset"][identifier]
                with open("mailmanager.json", "w") as f:
                    json.dump(data, f)
                serverly.logger.success(f"Changed password of {username}!")
                return True
        return False
    except (FileNotFoundError, json.JSONDecodeError):
        _set_up_mailmanager_json()
        reset_password(identifier, password)
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


def _set_up_mailmanager_json():
    f = open("mailmanager.json", "w+")
    d = {}
    for i in _default_special_emails.keys():
        d[i] = {}
    json.dump(d, f)
    f.close()


manager: MailManager = None


def setup(email_address: str, email_password: str, special_mails={}, online_url="", pending_interval=15, scheduled_interval=15, debug=False):
    global manager
    manager = MailManager(email_address, email_password, special_mails,
                          online_url, pending_interval, scheduled_interval, debug)
