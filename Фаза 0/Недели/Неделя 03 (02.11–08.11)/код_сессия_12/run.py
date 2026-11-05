from netrc_copy import netrc

creds = netrc("sample.netrc")
print(creds.authenticators("backup.teplydom.example"))
print(creds.authenticators("mail.teplydom.example"))
