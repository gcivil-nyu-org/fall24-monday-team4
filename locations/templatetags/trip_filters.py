from django import template

register = template.Library()


@register.filter
def accepted_matches_count(trip):
    return trip.received_matches.filter(status="ACCEPTED").count()


@register.filter
def sub(value, arg):
    return value - arg


@register.filter
def first_accepted_match(trip):
    return trip.received_matches.filter(status="ACCEPTED").first()
