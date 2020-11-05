# MassMail

Mass mailing via SMTP.

Features:

- Send bulk of emails.
- Randomize text of subject and message for each email.
- Attach files.
- Parallel processing.

Install:

```bash
# I recommend to use pipx instead
$ pip install massmail
```

Usage:

```bash
$ massmail --help
```

Example:

```bash
zcnbvm@proton.me --host smtp.gmail.com --ssl --port 465 --message "{Привет|Здравствуй}, {как {жизнь|дела}|что нового}?" emails.txt
```
