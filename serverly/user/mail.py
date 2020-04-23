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

        self.pending = []
        self.scheduled = []

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
        serverly.logger.success(f"Sent email to {email}!")

    def schedule(self, email: dict, immedieately=False, **kwargs):
        # TODO: make robust
        try:
            self._load()
            if immedieately:
                self.pending.append(email)
                self.send_pending()
            else:
                if type(email["schedule"]) == str:
                    email["schedule"] = datetime.datetime.fromisoformat(
                        email["schedule"])
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
            print("EXCEPTION")
            print(e)

    def send_pending(self):
        try:
            self._load()
            print("PENDING: ", self.pending)
            processes = []
            for mail in self.pending:
                def send():
                    self.send(mail["subject"], mail.get("content", ""),
                              mail.get("attachments", None), mail.get("username", None), mail.get("email", None))
                    self.pending.pop(self.pending.index(mail))
                    self._save()
                processes.append(multiprocessing.Process(
                    target=send, name="Sending of email"))
            for process in processes:
                process.start()
            for process in processes:
                process.join()
        except Exception as e:
            self._save()
            raise e

    def send_scheduled(self):
        try:
            self._load()
            print("SCHEDULED: ", self.scheduled)
            processes = []
            for mail in self.scheduled:
                def send():
                    self.send(mail["subject"], mail.get("content", ""),
                              mail.get("attachments", None), mail.get("username", None), mail.get("email", None))
                    self.scheduled.pop(self.scheduled.index(mail))
                    self._save()
                if datetime.datetime.now() >= mail["schedule"]:
                    processes.append(multiprocessing.Process(target=send))
            for process in processes:
                process.start()
            for process in processes:
                process.join()
        except Exception as e:
            self._save()
            raise e

    def start(self):
        def pending():
            try:
                while True:
                    self.send_pending()
                    print("Sent all pending!!!")
                    time.sleep(10)
            except KeyboardInterrupt:
                self._save()
            except Exception as e:
                print("EXCEPTION " + str(type(e)) + "\n" + str(e))

        def scheduled():
            try:
                while True:
                    self.send_scheduled()
                    print("Sent all scheduled!!!")
                    time.sleep(10)
            except KeyboardInterrupt:
                self._save()
            except Exception as e:
                print("EXCEPTION " + str(type(e)) + "\n" + str(e))

        self._load()

        pending_handler = multiprocessing.Process(
            target=pending, name="MailManager: Pending")
        scheduled_handler = multiprocessing.Process(
            target=scheduled, name="Mailmanager: Scheduled")

        pending_handler.start()
        scheduled_handler.start()

    def send_verification_mail(self, username: str = None, email: str = None):
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


def setup(email_address: str, email_password):  # TODO other paras
    global manager
    manager = MailManager(email_address, email_password)
