# -*- coding: utf-8 -*-
import logging
import multiprocessing
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial
from typing import BinaryIO, List, TextIO, Union

import click

__author__ = 'Sergey M'
__email__ = 'tz4678@gmail.com'
__license__ = 'MIT'
__version__ = '0.1.0'


@click.command()
@click.version_option(__version__)
@click.option('-u', '--username', help="username")
@click.option('-p', '--password', help="password")
@click.option('-h', '--host', help="host")
@click.option('--port', default=25, help="Port", show_default=True, type=int)
@click.option(
    '--ssl/--no-ssl',
    'use_ssl',
    default=False,
    help="use SSL",
    is_flag=True,
    show_default=True,
)
@click.option('--message', '-m', default="", help="message")
@click.option('--subject', '-s', default="", help="subject")
@click.option(
    '--as-html',
    default=False,
    help="send as HTML",
    is_flag=True,
    show_default=True,
)
@click.option(
    '--attach',
    '-a',
    'attachments',
    help="attach file",
    multiple=True,
    type=click.File('rb'),
)
@click.option(
    '--workers',
    '-w',
    'workers_num',
    default=max(multiprocessing.cpu_count() - 1, 1),
    help="number of workers",
    show_default=True,
    type=int,
)
@click.option(
    '--verbosity',
    '-v',
    count=True,
    help="increase output verbosity: 0 - warning, 1 - info, 2 - debug",
    show_default=True,
)
@click.argument(
    'emails_file',
    type=click.File('r', encoding='utf-8'),
)
def massmail(
    username: Union[None, str],
    password: Union[None, str],
    host: Union[None, str],
    port: int,
    use_ssl: bool,
    message: str,
    subject: str,
    as_html: bool,
    attachments: List[BinaryIO],
    workers_num: int,
    verbosity: int,
    emails_file: TextIO,
) -> None:
    """Mass Mailing via SMTP"""
    if not username:
        username = click.prompt("Username")
    if not password:
        password = click.prompt("Password", hide_input=True)
    if not host:
        host = click.prompt("Host")
    emails = emails_file.read().splitlines()
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, len(levels) - 1)]
    logger = multiprocessing.log_to_stderr(level)
    logger.info("start mailing")
    email_queue = multiprocessing.Queue()
    for email in emails:
        email_queue.put(email)
    workers = [
        Worker(
            email_queue,
            username,
            password,
            host,
            port,
            use_ssl,
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
        username: str,
        password: str,
        host: str,
        port: int,
        use_ssl: bool,
        message: str,
        subject: str,
        as_html: bool,
        attachments: List[BinaryIO],
    ) -> None:
        super().__init__(daemon=True)
        self.email_queue = email_queue
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.message = message
        self.as_html = as_html
        self.subject = subject
        self.attachments = attachments
        self.logger = multiprocessing.get_logger()
        self.start()

    def connect(self) -> None:
        if hasattr(self, 'smtp'):
            return
        if self.use_ssl:
            self.smtp = smtplib.SMTP_SSL(self.host, self.port)
        else:
            self.smtp = smtplib.SMTP(self.host, self.port)
        self.smtp.login(self.username, self.password)

    def run(self) -> None:
        while self.email_queue.qsize() > 0:
            email = self.email_queue.get()
            try:
                msg = MIMEMultipart()
                msg['From'] = self.username
                msg['To'] = email
                msg['Subject'] = self.subject
                msg.attach(
                    MIMEText(self.message, 'html' if self.as_html else 'plain')
                )
                for attachment in self.attachments:
                    part = MIMEBase('application', 'octeat-stream')
                    attachment.seek(0)
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        # не смог я нагуглить как закодировать имя, содержащее двойные кавычки
                        f'attachment; filename="{os.path.basename(attachment.name)}"',
                    )
                    msg.attach(part)
                self.connect()
                self.smtp.sendmail(self.username, email, msg.as_string())
            except Exception as e:
                self.logger.error(e)
