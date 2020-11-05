# MassMail

Mass mailing via SMTP.

Install:

```bash
$ pipx install massmail
```

Example:

```bash
$ massmail --username your-account@gmail.com --host smtp.gmail.com --ssl --port 465 --subject "Special Offer" --attach offer.pdf emails.txt
```
