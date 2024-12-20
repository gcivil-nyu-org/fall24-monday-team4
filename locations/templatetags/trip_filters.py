from django import template
from django.db.models import Q

from locations.models import Match, Trip, UserLocation
from django.contrib.auth.models import User


register = template.Library()


@register.filter
def has_panic_users(trip):
    # Get all connected users through matches
    connected_users = User.objects.filter(
        (
            Q(trip__matches__trip2=trip, trip__matches__status="ACCEPTED")
            | Q(trip__matched_with__trip2=trip, trip__matched_with__status="ACCEPTED")
            | Q(trip__matches__trip1=trip, trip__matches__status="ACCEPTED")
            | Q(trip__matched_with__trip1=trip, trip__matched_with__status="ACCEPTED")
        )
    ).distinct()

    # Check if any user has panic mode on
    return UserLocation.objects.filter(user__in=connected_users, panic=True).exists()


@register.filter
def all_matches(trip):
    return Match.objects.filter(Q(trip1=trip) | Q(trip2=trip)).distinct()


@register.filter
def sub(value, arg):
    return value - arg


@register.filter
def completion_votes_count(trip):
    # Count all connected trips that have requested completion
    connected_votes = Trip.objects.filter(
        (
            Q(matches__trip2=trip, matches__status="ACCEPTED")
            | Q(matched_with__trip2=trip, matched_with__status="ACCEPTED")
            | Q(matches__trip1=trip, matches__status="ACCEPTED")
            | Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")
        ),
        completion_requested=True,
    ).count()

    # Add current trip's vote if it has requested completion
    return connected_votes


@register.filter
def total_group_members(trip):
    # Count all connected trips using the same query pattern
    connected_trips = Trip.objects.filter(
        (
            Q(matches__trip2=trip, matches__status="ACCEPTED")
            | Q(matched_with__trip2=trip, matched_with__status="ACCEPTED")
            | Q(matches__trip1=trip, matches__status="ACCEPTED")
            | Q(matched_with__trip1=trip, matched_with__status="ACCEPTED")
        )
    ).count()
    return connected_trips  # Add 1 for current trip


@register.filter
def has_pending_match(match_trip, user_trip):
    return (
        match_trip.matches.filter(trip2=user_trip, status="PENDING").exists()
        or user_trip.matches.filter(trip2=match_trip, status="PENDING").exists()
    )
