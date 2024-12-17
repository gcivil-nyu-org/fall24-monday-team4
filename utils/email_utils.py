from django.core.mail import EmailMessage
from django.conf import settings
import re


def FamilyMemberEmails(memberEmails, htmlMessage, subjectTxt):
    subject = subjectTxt
    html_message = htmlMessage
    email = EmailMessage(
        subject, html_message, settings.DEFAULT_FROM_EMAIL, memberEmails
    )
    email.content_subtype = "html"
    email.send()


def validate_family_members_input(data):
    for member in data:
        if (
            not member.get("name")
            or not isinstance(member.get("name"), str)
            or member["name"].strip() == ""
        ):
            return False, "Invalid or empty name"

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not member.get("email") or not re.match(email_regex, member["email"]):
            return (
                False,
                f"Invalid email format: {member.get('email', 'No email provided')}",
            )

    return True, "Valid Format"
