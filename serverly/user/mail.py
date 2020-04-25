import datetime
import json
import multiprocessing
import re
import string
import time
from functools import wraps

import serverly
import yagmail
from serverly.utils import ranstr

_default_verification_subject = "Your recent registration"
_default_verification_template = """Hey $username,
thank you for registering for our service. Please click <a href='$verification_url'>this link</a> to verify your email.

If you cannot click the link for some reason, you can also just copy/paste it:
$verification_url
"""


class MailManager:
    def __init__(self, email_address: str, email_password: str, verification_subject=None, verification_template: str = None, online_url: str = "", pending_interval=15, scheduled_interval=15):
        self._email_address = None
        self._email_password = None
        self._verification_subject = None
        self._verification_template = None
        self._online_url = None

        self.email_address = email_address
        self.email_password = email_password
        self.verification_subject = verification_subject
        self.verification_template = verification_template
        self.online_url = online_url

        self.pending = []
        self.scheduled = []

        self.pending_interval = int(pending_interval)
        self.scheduled_interval = int(scheduled_interval)

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
    def verification_subject(self):
        if self._verification_template != None:
            return str(self._verification_subject)
        else:
            return _default_verification_subject

    @verification_subject.setter
    def verification_subject(self, verification_subject: str):
        self._verification_subject = str(
            verification_subject) if verification_subject != None else _default_verification_subject

    @property
    def verification_template(self):
        if self._verification_template != None:
            return str(self._verification_template)
        else:
            return _default_verification_template

    @verification_template.setter
    def verification_template(self, verification_template: str):
        self._verification_template = str(
            verification_template) if verification_template != None else _default_verification_template

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
                user = serverly.user.get_by_email(email)
            if substitute:
                subject_temp = string.Template(subject)
                content_temp = string.Template(content)

                d = user.to_dict()

                subject = subject_temp.safe_substitute(**d)
                content = content_temp.safe_substitute(**d)

            self.yag.send(email, subject, content, attachments)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            serverly.logger.handle_exception(e)
            raise e

    def schedule(self, email={}, immediately=True):
        """schedule a new email: dict. 'email' or 'username' as well as 'subject' are required. Use 'schedule': Union[isoformat, datetime.datetime] to schedule it for some time in the future. Required if 'immediately' is False. If 'immediately' is True, send it ASAP."""
        try:
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
                                  mail.get("attachments", None), mail.get("username", None), mail.get("email", None), True)
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
                        f"Sent {str(n)} pending emails", False)
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
                        f"Sent {str(n)} scheduled emails", False)
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

    def send_verification_mail(self, username: str):
        try:
            identifier = ranstr()
            verification_url = self.online_url + \
                serverly._sitemap.superpath + "verify/" + identifier
            substitutions = {**serverly.user.get(username).to_dict(),
                             **{"verification_url": verification_url}}
            for key, value in substitutions.items():
                substitutions[key] = str(value)

            subject_temp = string.Template(self.verification_subject)
            content_temp = string.Template(self.verification_template)

            subject = subject_temp.substitute(substitutions)
            content = content_temp.substitute(substitutions)

            try:
                self.send(subject, content, username=username)
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


def verify(identifier: str):
    try:
        with open("pending_verifications.json", "r") as f:
            data = json.load(f)
        for identi, username in data.items():
            if identi == identifier:
                serverly.user.change(username, verified=True)
                del data[identifier]
                with open("pending_verifications.json", "w") as f:
                    json.dump(data, f)
                return
        serverly.logger.success(f"verified email of {username}!")
    except Exception as e:
        serverly.logger.handle_exception(e)
        raise e


manager: MailManager = None


def setup(email_address: str, email_password: str, verification_subject_template: str = None, verification_content_template: str = None, online_url="", pending_interval=15, scheduled_interval=15):
    global manager
    manager = MailManager(email_address, email_password, verification_subject_template,
                          verification_content_template, online_url, pending_interval, scheduled_interval)
