# MassMail

Mass mailing via SMTP.

Features:

- Send bulk of emails.
- Randomize text of subject and message for each email.
- Attach files.

Install:

```bash
# I recommend to use pipx instead
$ pip install massmail
```

Example:

```bash
$ massmail --username your-account@gmail.com --host smtp.gmail.com --ssl --port 465 --message "{Привет|Здравствуй}, {как {жизнь|дела}|что нового}?" emails.txt
```
