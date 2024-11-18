from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _


# Function to validate only nyu.edu email addresses for sign up
def validate_email_domain(value):
    """
    Validate if the email domain is valid.
    """
    try:
        validator = EmailValidator()
        validator(value)

        # Extract the domain part of the email address
        domain = value.split("@")[1]

        if domain != "nyu.edu":
            raise ValidationError(_("Invalid email domain."))

    except ValidationError:
        raise ValidationError(_("Invalid email address."))
