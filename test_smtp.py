# test_smtp.py — put this in your project root and run it
import smtplib

with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
    server.starttls()
    server.login("abfda9f71524b3", "cb0ed5f95190cc")
    server.sendmail(
        "noreply@nurselink.com",
        "ahmed@example.com",
        "Subject: Test\n\nHello from NurseLink"
    )
    print("Email sent successfully!")