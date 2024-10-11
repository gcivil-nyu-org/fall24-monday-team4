from django.core.validators import EmailValidator
from django.utils.deconstruct import deconstructible

@deconstructible
class NyuEmailValidator(EmailValidator):
    def validate_domain_part(self, domain_part):
        return False
    
    def __eq__(self, other):
        return isinstance(other, NyuEmailValidator) and super().__eq__(other)