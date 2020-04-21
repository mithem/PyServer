import json
import multiprocessing
import re
import string
import time
from functools import wraps

import serverly
import yagmail
import datetime


class MailManager:
    def __init__(self, email_address: str, email_password: str, verification_subject=None, verification_template: str = None, online_url: str = ""):
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
        self.pending, self.scheduled = self._load()

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
        return self._verification_subject

    @verification_subject.setter
    def verification_subject(self, verification_subject: str):
        self._verification_subject = str(verification_subject) if type(
            verification_subject) != None else None

    @property
    def verification_template(self):
        return self._verification_template

    @verification_template.setter
    def verification_template(self, verification_template: str):
        self._verification_template = str(verification_template) if type(
            verification_template) != None else None

    @property
    def online_url(self):
        return self._online_url

    @online_url.setter
    def online_url(self, online_url: str):
        url_pattern = r"https?: \/\/(www\.)?[-a-zA-Z0-9@: % ._\+ ~  # =]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        if not re.match(url_pattern, str(online_url)) and not online_url == "":
            raise ValueError("Online_url appears to be invalid.")
        self._online_url = str(online_url)

    def send(self, subject: str, content="", attachments=None, username: str = None, email: str = None):
        """send email immediately and without multiprocessing"""
        if username != None:
            email = serverly.user.get(str(username)).email
        elif email == None:
            return serverly.logger.warning("Cannot send email: Neither username nor email provieded.", extra_context="MAIL")
        self.yag.send(email, subject, content, attachments)

    def schedule(self, email: dict, immedieately=False, **kwargs):
        # TODO: make robust
        try:
            if immedieately:
                self.pending.append(email)
            else:
                self.scheduled.append(email)
            self._save()
        except Exception as e:
            serverly.logger.handle_exception(e)

    def _load(self):
        """return pending: list, scheduled: list emails as a tuple"""
        try:
            with open("mails.json", "r") as f:
                data = json.load(f)
            for obj in data["scheduled"]:
                obj["schedule"] = datetime.datetime.fromisoformat(
                    obj["schedule"])
            return data["pending"], data["scheduled"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
            return [], []

    def _save(self):
        with open("mails.json", "w+") as f:
            json.dump({"pending": self.pending,
                       "scheduled": self.scheduled}, f)

    def send_pending(self):
        processes = []
        for mail in self.pending:
            def send():
                self.send(mail["subject"], mail.get("content", ""),
                          mail.get("attachments", None), mail.get("username", None), mail.get("email", None))
                self.pending.pop(self.pending.index(mail))
            processes.append(multiprocessing.Process(target=send, args=(mail["subject"], mail.get(
                "content", None), mail.get("attachments", None), mail.get("username", None), mail.get("email", None)), name="Sending of email"))
        for process in processes:
            process.start()
        for process in processes:
            process.join()

    def send_scheduled(self):
        processes = []
        for mail in self.scheduled:
            def send():
                self.send(mail["subject"], mail.get("content", ""),
                          mail.get("attachments", None), mail.get("username", None), mail.get("email", None))
                self.scheduled.pop(self.scheduled.index(mail))
            if datetime.datetime.now() >= mail["schedule"]:
                processes.append(multiprocessing.Process(target=send))
        for process in processes:
            process.start()
        for process in processes:
            process.join()

    def start(self):
        def pending():
            try:
                while True:
                    self.send_pending()
                    print("Sent all pending!!!")
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print("EXCEPTION " + str(type(e)) + "\n" + str(e))

        def scheduled():
            try:
                while True:
                    self.send_scheduled()
                    print("Sent all scheduled!!!")
                    time.sleep(30)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print("EXCEPTION " + str(type(e)) + "\n" + str(e))

        pending_handler = multiprocessing.Process(
            target=pending, name="MailManager: Pending")
        scheduled_handler = multiprocessing.Process(
            target=scheduled, name="Mailmanager: Scheduled")

        pending_handler.start()
        scheduled_handler.start()


manager: MailManager = None


def setup(email_address: str, email_password):  # TODO other paras
    global manager
    manager = MailManager(email_address, email_password)
