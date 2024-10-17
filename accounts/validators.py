from django.core.validators import EmailValidator
from django.utils.deconstruct import deconstructible

# Function to validate only nyu.edu email addresses for sign up
@deconstructible
class NyuEmailValidator(EmailValidator):
    def validate_domain_part(self, domain_part):
        return False
    
    def __eq__(self, other):
        return isinstance(other, NyuEmailValidator) and super().__eq__(other)