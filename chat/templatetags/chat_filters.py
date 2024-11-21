from django import template

register = template.Library()


@register.filter
def css_for_messagetype(message_type):
    css_tag = None

    if message_type == "SYSTEM":
        css_tag = "system-message"
    elif message_type == "EMS_SYSTEM":
        css_tag = "ems-system-message"
    elif message_type == "EMS_PANIC_MESSAGE":
        css_tag = "panic-message"

    return css_tag
