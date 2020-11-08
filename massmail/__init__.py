# -*- coding: utf-8 -*-
# TODO: check TLS
import logging
import multiprocessing
import os
import random
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import BinaryIO, TextIO, Tuple, Union

import click

__author__ = 'Sergey M'
__email__ = 'tz4678@gmail.com'
__license__ = 'MIT'
__version__ = '0.1.2'


@click.command()
@click.version_option(__version__)
@click.option('-H', '--host', help="Host", required=True)
@click.option('-U', '--username', help="Username", required=True)
@click.option('-P', '--password', help="Password")
@click.option(
    '--port',
    '-p',
    default=smtplib.SMTP_PORT,
    help="Port",
    show_default=True,
    type=int,
)
@click.option(
    '--ssl/--no-ssl',
    default=False,
    help="Use SSL",
    is_flag=True,
    show_default=True,
)
@click.option(
    '--starttls',
    default=False,
    help="Start TLS",
    is_flag=True,
    show_default=True,
)
@click.option('--sender-name', help="Sender name")
@click.option(
    '--bcc',
    help="Blind carbon copy. This option can be specified several times",
    multiple=True,
)
@click.option('--reply-to', help="Email reply address")
@click.option('--reply-name', help="Email reply name")
@click.option('--message', '-m', default='', help="Message")
@click.option('--subject', '-s', default='', help="Subject")
@click.option(
    '--as-html',
    default=False,
    help="Send as HTML",
    is_flag=True,
    show_default=True,
)
@click.option(
    '--attach',
    '-a',
    'attachments',
    help="Attach file. This option can be specified several times",
    multiple=True,
    type=click.File('rb'),
)
@click.option(
    '--workers',
    '-w',
    'workers_num',
    default=max(multiprocessing.cpu_count() - 1, 1),
    help="Number of worker processes",
    show_default=True,
    type=int,
)
@click.option(
    '--verbosity',
    '-v',
    count=True,
    help="Increase output verbosity: 0 - warning, 1 - info, 2 - debug",
    show_default=True,
)
@click.argument(
    'emails_file',
    type=click.File('r', encoding='utf-8'),
)
def massmail(
    host: str,
    username: str,
    password: Union[None, str],
    port: int,
    ssl: bool,
    starttls: bool,
    sender_name: Union[None, str],
    bcc: Tuple[str],
    reply_to: Union[None, str],
    reply_name: Union[None, str],
    message: str,
    subject: str,
    as_html: bool,
    attachments: Tuple[BinaryIO],
    workers_num: int,
    verbosity: int,
    emails_file: TextIO,
) -> None:
    """Mass Mailing via SMTP"""
    # Не сохраняем пароль в истории
    if not password:
        password = click.prompt("Password", hide_input=True)
    emails = emails_file.read().splitlines()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, len(levels) - 1)]
    logger = multiprocessing.log_to_stderr(level)
    email_queue = multiprocessing.Queue()
    for email in emails:
        email_queue.put(email)
    workers_num = min(workers_num, len(emails))
    logger.info("start mailing")
    workers = [
        Worker(
            email_queue,
            host,
            username,
            password,
            port,
            ssl,
            starttls,
            sender_name,
            bcc,
            reply_to,
            reply_name,
            message,
            subject,
            as_html,
            attachments,
        )
        for _ in range(workers_num)
    ]
    for worker in workers:
        worker.join()
    logger.info("finished mailing")


class Worker(multiprocessing.Process):
    def __init__(
        self,
        email_queue: multiprocessing.Queue,
        host: str,
        username: str,
        password: str,
        port: int,
        ssl: bool,
        starttls: bool,
        sender_name: Union[None, str],
        bcc: Tuple[str],
        reply_to: Union[None, str],
        reply_name: Union[None, str],
        message: str,
        subject: str,
        as_html: bool,
        attachments: Tuple[BinaryIO],
    ) -> None:
        super().__init__(daemon=True)
        self.email_queue = email_queue
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.ssl = ssl
        self.starttls = starttls
        self.sender_name = sender_name
        self.bcc = bcc
        self.reply_to = reply_to
        self.reply_name = reply_name
        self.message = message
        self.as_html = as_html
        self.subject = subject
        self.attachments = attachments
        self.logger = multiprocessing.get_logger()
        self.start()

    @property
    def connection(self) -> None:
        return smtplib.SMTP_SSL if self.ssl else smtplib.SMTP

    def login(self) -> None:
        self.smtp = self.connection(self.host, self.port)
        if self.ssl and self.starttls:
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.ehlo()
        self.smtp.login(self.username, self.password)

    def send(self, to: str) -> None:
        message = MIMEMultipart()
        message['From'] = make_address(self.username, self.sender_name)
        message['To'] = to
        if self.reply_to:
            message['Reply-To'] = make_address(self.reply_to, self.reply_name)
        if self.bcc:
            message['BCC'] = ', '.join(self.bcc)
        message['Subject'] = randomize(self.subject)
        message.attach(
            MIMEText(
                randomize(self.message),
                'html' if self.as_html else 'plain',
            )
        )
        for attachment in self.attachments:
            part = MIMEBase('application', 'octeat-stream')
            attachment.seek(0)
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            filename = os.path.basename(attachment.name)
            # На rambler.ru не работает
            # https://tools.ietf.org/html/rfc6266#section-5
            # part.add_header(
            #     'Content-Disposition',
            #     f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}",
            # )
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{filename}"',
            )
            message.attach(part)
        self.smtp.sendmail(self.username, to, message.as_string())

    def run(self) -> None:
        self.login()
        while self.email_queue.qsize() > 0:
            email = self.email_queue.get()
            try:
                self.send(email)
            except Exception as e:
                self.logger.fatal(e)
                raise


def randomize(s: str) -> str:
    """Randomize text.

    >>> randomize('{Привет|Здравствуй}, {как {жизнь|дела}|что нового}?')
    'Привет, как жизнь?'
    """
    while 1:
        temp = re.sub(
            r'{([^{}]*)}', lambda m: random.choice(m.group(1).split('|')), s
        )
        if s == temp:
            break
        s = temp
    return s


def make_address(email: str, name: Union[None, str]) -> str:
    if name:
        return formataddr((name, email))
    return email
