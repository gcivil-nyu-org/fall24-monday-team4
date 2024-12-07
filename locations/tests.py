# from django.test import TestCase

# Create your tests here.

from unittest.mock import call, patch
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Trip, Match, UserLocation
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from chat.models import ChatRoom, Message
from locations.views import send_ems_message, send_system_message

from locations.templatetags.trip_filters import (
    all_matches,
    completion_votes_count,
    total_group_members,
    has_pending_match,
    sub,
)


class LocationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user.userprofile.is_verified = True
        self.user.userprofile.save()

        self.user2 = User.objects.create_user(
            username="testuser2", password="testpass2"
        )
        self.user2.userprofile.is_verified = True
        self.user2.userprofile.save()

        self.client.login(username="testuser", password="testpass")

        # Create a base trip for testing
        self.trip = Trip.objects.create(
            user=self.user,
            start_latitude="40.7128",
            start_longitude="-74.0060",
            dest_latitude="40.7580",
            dest_longitude="-73.9855",
            status="SEARCHING",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
        )

        self.location = UserLocation.objects.create(
            user=self.user, latitude=40.7128, longitude=-74.0060
        )

    def test_complete_trip_with_majority_previous_trips(self):
        # Setup trips and match
        self.trip.status = "IN_PROGRESS"
        self.trip.save()

        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
            completion_requested=True,  # Other user already voted
        )

        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        # Test completing trip
        response = self.client.post(reverse("complete_trip"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("previous_trips"))

        self.trip.refresh_from_db()
        matched_trip.refresh_from_db()
        self.assertEqual(self.trip.status, "COMPLETED")
        self.assertEqual(matched_trip.status, "COMPLETED")

    def test_get_trip_locations(self):
        # Update the base trip status to IN_PROGRESS
        self.trip.status = "IN_PROGRESS"  # Add this line
        self.trip.save()  # Add this line

        # Create a matched trip
        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
        )

        # Create a match between trips
        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        # Create location for matched user
        UserLocation.objects.create(
            user=self.user2, latitude="40.7129", longitude="-74.0061"
        )

        response = self.client.get(reverse("get_trip_locations"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_start_trip(self):
        # Test transition from MATCHED to READY
        self.trip.status = "MATCHED"
        self.trip.save()

        response = self.client.post(reverse("start_trip"))
        self.assertEqual(response.status_code, 302)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "READY")

    def test_complete_trip(self):
        # Setup an in-progress trip with a match
        self.trip.status = "IN_PROGRESS"
        self.trip.save()

        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
        )

        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        response = self.client.post(reverse("complete_trip"))
        self.assertEqual(response.status_code, 302)

        self.trip.refresh_from_db()
        self.assertTrue(self.trip.completion_requested)

    def test_handle_match_request(self):
        # Create a pending match
        match = Match.objects.create(
            trip1=Trip.objects.create(
                user=self.user2,
                start_latitude="40.7129",
                start_longitude="-74.0061",
                dest_latitude="40.7581",
                dest_longitude="-73.9856",
                status="SEARCHING",
                planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            ),
            trip2=self.trip,
            status="PENDING",
        )

        response = self.client.post(
            reverse("handle_match_request"), {"match_id": "asdasd", "action": 99}
        )
        self.assertEqual(response.status_code, 400)

        # Test accepting match
        response = self.client.post(
            reverse("handle_match_request"), {"match_id": match.id, "action": "accept"}
        )
        self.assertEqual(response.status_code, 302)

        match.refresh_from_db()
        self.assertEqual(match.status, "ACCEPTED")

    def test_previous_trips(self):
        # Create a completed trip
        Trip.objects.create(
            user=self.user,
            start_latitude="40.7128",
            start_longitude="-74.0060",
            dest_latitude="40.7580",
            dest_longitude="-73.9855",
            status="COMPLETED",
            planned_departure=make_aware(datetime.now() - timedelta(days=1)),
        )

        response = self.client.get(reverse("previous_trips"))
        self.assertEqual(response.status_code, 200)

    def test_create_trip(self):
        data = {
            "planned_departure": (datetime.now() + timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "start_latitude": "40.7128",
            "start_longitude": "-74.0060",
            "dest_latitude": "40.7580",
            "dest_longitude": "-73.9855",
            "start_address": "start",
            "end_address": "end",
            "desired_companions": 1,
            "search_radius": 200,
        }
        response = self.client.post(reverse("create_trip"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        self.assertTrue(Trip.objects.filter(user=self.user).exists())

        response = self.client.get(reverse("create_trip"))
        self.assertEqual(response.status_code, 405)

    def test_update_location(self):
        data = {"latitude": "40.7128", "longitude": "-74.0060"}
        response = self.client.post(reverse("update_location"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserLocation.objects.filter(user=self.user).exists())

    def test_cancel_trip(self):
        response = self.client.post(reverse("cancel_trip"))
        self.assertEqual(response.status_code, 302)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "CANCELLED")

    @patch("locations.views.broadcast_trip_update")
    def test_cancel_trip_exception(self, mock_broadcast):
        # Create potential match trip
        Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=self.trip.planned_departure,
            desired_companions=1,
            search_radius=200,
        )

        # Make broadcast throw error
        mock_broadcast.side_effect = Exception("Broadcasting error")

        response = self.client.post(reverse("cancel_trip"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Broadcasting error")

    @patch("locations.views.UserLocation.objects.filter")
    def test_get_trip_locations_exception(self, mock_filter):
        # Setup in-progress trip
        self.trip.status = "IN_PROGRESS"
        self.trip.save()

        # Make the filter query raise an exception
        mock_filter.side_effect = Exception("Database query failed")

        response = self.client.get(reverse("get_trip_locations"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Database query failed")

    @patch("locations.views.broadcast_trip_update")
    def test_send_match_request_exception(self, mock_broadcast):
        potential_trip = Trip.objects.create(
            user=self.user2,
            status="SEARCHING",
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            planned_departure=self.trip.planned_departure,
            desired_companions=1,
        )

        mock_broadcast.side_effect = Exception("Match request broadcast failed")

        response = self.client.post(
            reverse("send_match_request"),
            {"trip_id": potential_trip.id, "action": "send"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Match request broadcast failed")

    @patch("locations.views.broadcast_trip_update")
    def test_handle_match_request_exception(self, mock_broadcast):
        # Create pending match
        other_trip = Trip.objects.create(
            user=self.user2,
            status="SEARCHING",
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            planned_departure=self.trip.planned_departure,
        )

        match = Match.objects.create(
            trip1=other_trip, trip2=self.trip, status="PENDING"
        )

        mock_broadcast.side_effect = Exception("Match handling broadcast failed")

        response = self.client.post(
            reverse("handle_match_request"), {"match_id": match.id, "action": "accept"}
        )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Match handling broadcast failed")

    def test_send_match_request(self):
        # Create another trip to match with
        other_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
        )

        # Test sending match request
        response = self.client.post(
            reverse("send_match_request"),
            {"trip_id": other_trip.id, "action": "request"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Match.objects.filter(trip1=self.trip, trip2=other_trip).exists()
        )

    def test_send_match_request_cancel(self):
        # Create another trip and a pending match
        other_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
        )

        Match.objects.create(trip1=self.trip, trip2=other_trip, status="PENDING")

        # Test canceling match request
        response = self.client.post(
            reverse("send_match_request"),
            {"trip_id": other_trip.id, "action": "cancel"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Match.objects.filter(trip1=self.trip, trip2=other_trip).exists()
        )

    def test_decline_match_request(self):
        # Create a pending match
        other_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
        )

        match = Match.objects.create(
            trip1=other_trip, trip2=self.trip, status="PENDING"
        )

        # Test declining match request
        response = self.client.post(
            reverse("handle_match_request"), {"match_id": match.id, "action": "decline"}
        )
        self.assertEqual(response.status_code, 302)

        match.refresh_from_db()
        self.assertEqual(match.status, "DECLINED")

    def test_complete_trip_with_majority(self):
        # Setup trips and match
        self.trip.status = "IN_PROGRESS"
        self.trip.save()

        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
            completion_requested=True,  # Other user already voted
        )

        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        # Test completing trip
        response = self.client.post(reverse("complete_trip"))
        self.assertEqual(response.status_code, 302)

        self.trip.refresh_from_db()
        matched_trip.refresh_from_db()
        self.assertEqual(self.trip.status, "COMPLETED")
        self.assertEqual(matched_trip.status, "COMPLETED")

    def test_current_trip_no_active(self):
        # Delete the trip created in setUp
        self.trip.delete()

        response = self.client.get(reverse("current_trip"))
        self.assertEqual(response.status_code, 200)

    def test_get_trip_locations_with_decorator(self):
        self.trip.delete()
        response = self.client.get(
            reverse("get_trip_locations"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(), {"success": False, "message": "No Active Trip Found."}
        )

    def test_current_trip_with_potential_match(self):
        """Test current_trip view when potential matches exist"""
        # Create a potential match trip with similar parameters
        potential_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",  # Very close to self.trip
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=self.trip.planned_departure,  # Same departure window
            desired_companions=1,
            search_radius=200,
        )

        response = self.client.get(reverse("current_trip"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "locations/current_trip.html")

        # Check context data
        self.assertEqual(response.context["user_trip"], self.trip)
        self.assertEqual(list(response.context["potential_matches"]), [potential_trip])
        self.assertEqual(list(response.context["received_matches"]), [])
        self.assertEqual(response.context["pusher_key"], settings.PUSHER_KEY)
        self.assertEqual(response.context["pusher_cluster"], settings.PUSHER_CLUSTER)

    def test_get_trip_locations_no_trip(self):
        """Test get_trip_locations when no trip exists"""
        self.trip.delete()
        response = self.client.get(reverse("get_trip_locations"))
        self.assertRedirects(response, reverse("home"))

    def test_update_location_error(self):
        """Test update_location with invalid data"""
        data = {"latitude": "invalid", "longitude": "invalid"}
        response = self.client.post(reverse("update_location"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])

    def test_start_trip_with_all_ready(self):
        """Test when all matched trips are ready"""
        # Setup main trip
        self.trip.status = "READY"
        self.trip.save()

        # Create matched trip that's also ready
        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="READY",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
        )

        # Create accepted match
        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        response = self.client.post(reverse("start_trip"))
        self.assertEqual(response.status_code, 302)

        self.trip.refresh_from_db()
        matched_trip.refresh_from_db()
        self.assertEqual(self.trip.status, "IN_PROGRESS")
        self.assertEqual(matched_trip.status, "IN_PROGRESS")

    def test_send_match_request_invalid_method(self):
        """Test send_match_request with GET method"""
        response = self.client.get(reverse("send_match_request"))
        self.assertEqual(response.status_code, 405)

    def test_cancel_nonexistent_trip(self):
        """Test cancelling when no active trip exists"""
        self.trip.delete()
        response = self.client.post(reverse("cancel_trip"))
        self.assertEqual(response.status_code, 302)

    def test_get_h3_resolution_and_ring_size(self):
        """Test H3 resolution and ring size calculations for different radii"""
        from locations.views import get_h3_resolution_and_ring_size

        # Test different radius values
        test_cases = [
            (100, 11, 2),  # Small radius
            (200, 10, 1),  # Default search radius
            (500, 9, 1),  # Medium radius
            (1000, 8, 1),  # Large radius
        ]

        for radius, expected_res, expected_ring in test_cases:
            resolution, ring_size = get_h3_resolution_and_ring_size(radius)
            self.assertEqual(
                resolution,
                expected_res,
                f"Expected resolution {expected_res} for radius {radius}, got {resolution}",
            )
            self.assertEqual(
                ring_size,
                expected_ring,
                f"Expected ring size {expected_ring} for radius {radius}, got {ring_size}",
            )

    def test_send_system_message(self):
        """Test sending system message to chat room"""

        chatroom = ChatRoom.objects.create(name="Test Room")
        test_message = "Test system message"

        send_system_message(chatroom, test_message)

        message = Message.objects.filter(chat_room=chatroom).first()
        self.assertIsNotNone(message)
        self.assertEqual(message.message, test_message)
        self.assertEqual(message.message_type, "SYSTEM")

    def test_handle_match_request_value_error(self):
        """Test handle_match_request when trip is no longer accepting matches"""
        # Create match with a trip that's not in SEARCHING state
        self.trip.status = "MATCHED"
        self.trip.save()

        match = Match.objects.create(
            trip1=Trip.objects.create(
                user=self.user2,
                start_latitude="40.7129",
                start_longitude="-74.0061",
                dest_latitude="40.7581",
                dest_longitude="-73.9856",
                status="SEARCHING",
                planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            ),
            trip2=self.trip,
            status="PENDING",
        )

        response = self.client.post(
            reverse("handle_match_request"), {"match_id": match.id, "action": "accept"}
        )
        self.assertEqual(response.status_code, 400)

    def test_handle_match_request_exceptions(self):
        """Test handle_match_request different exceptions"""
        # Test Match.DoesNotExist
        response = self.client.post(
            reverse("handle_match_request"), {"match_id": 99999, "action": "accept"}
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse("handle_match_request"))
        self.assertEqual(response.status_code, 405)

        # Test general exception
        response = self.client.post(
            reverse("handle_match_request"), {"action": "accept"}  # Missing match_id
        )
        self.assertEqual(response.status_code, 404)

    def test_send_match_request_exceptions(self):
        """Test send_match_request exception handling"""
        self.trip.delete()
        # Test with invalid trip_id
        response = self.client.post(
            reverse("send_match_request"), {"trip_id": 99999, "action": "send"}
        )
        self.assertRedirects(response, reverse("home"))

        # Test with missing data
        response = self.client.post(
            reverse("send_match_request"), {"action": "send"}  # Missing trip_id
        )
        self.assertRedirects(response, reverse("home"))

    def test_complete_trip_redirect_to_previous_trips(self):
        """Test complete_trip redirects correctly when enough votes are received"""
        # Setup trip with IN_PROGRESS status
        self.trip.status = "IN_PROGRESS"
        self.trip.save()

        # Create matched trip with completion already requested
        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            completion_requested=True,  # Other user already voted
        )

        # Create accepted match between trips
        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        # Test the redirect when requesting completion
        response = self.client.post(reverse("complete_trip"))
        self.assertRedirects(response, reverse("previous_trips"))

        # Verify both trips are completed
        self.trip.refresh_from_db()
        matched_trip.refresh_from_db()
        self.assertEqual(self.trip.status, "COMPLETED")
        self.assertEqual(matched_trip.status, "COMPLETED")

    def test_complete_trip_invalid_request(self):
        """Test complete_trip redirects to current_trip when not enough votes"""
        # Setup trip with IN_PROGRESS status

        response = self.client.get(reverse("complete_trip"))
        self.assertEqual(response.status_code, 405)

    def test_complete_trip_redirect_to_current_trip(self):
        """Test complete_trip redirects to current_trip when not enough votes"""
        # Setup trip with IN_PROGRESS status and completion_requested = False
        self.trip.status = "IN_PROGRESS"
        self.trip.completion_requested = True
        self.trip.save()

        # Create a matched trip that has already requested completion
        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            completion_requested=False,
        )

        # Create an accepted match between the trips
        Match.objects.create(trip1=self.trip, trip2=matched_trip, status="ACCEPTED")

        response = self.client.post(reverse("complete_trip"))
        self.assertRedirects(response, reverse("current_trip"))

    def test_complete_trip_lifecycle(self):
        """Test full trip lifecycle: matching, ready, in_progress, and completion"""
        # Create second user's trip with compatible parameters
        trip2 = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",  # Close to self.trip
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=self.trip.planned_departure,
            desired_companions=1,
            search_radius=200,
        )

        # First user sends match request
        response = self.client.post(
            reverse("send_match_request"), {"trip_id": trip2.id, "action": "send"}
        )
        self.assertTrue(response.json()["success"])

        # Second user accepts match request
        self.client.logout()
        self.client.login(username="testuser2", password="testpass2")
        match = Match.objects.get(trip1=self.trip, trip2=trip2)
        response = self.client.post(
            reverse("handle_match_request"), {"match_id": match.id, "action": "accept"}
        )
        self.assertRedirects(response, reverse("current_trip"))

        # Verify both trips are now matched
        self.trip.refresh_from_db()
        trip2.refresh_from_db()
        self.assertEqual(self.trip.status, "MATCHED")
        self.assertEqual(trip2.status, "MATCHED")

        # First user marks ready
        self.client.logout()
        self.client.login(username="testuser", password="testpass")
        response = self.client.post(reverse("start_trip"))
        self.assertRedirects(response, reverse("current_trip"))

        # Second user marks ready
        self.client.logout()
        self.client.login(username="testuser2", password="testpass2")
        response = self.client.post(reverse("start_trip"))
        self.assertRedirects(response, reverse("current_trip"))

        # Verify both trips are now in progress
        self.trip.refresh_from_db()
        trip2.refresh_from_db()
        self.assertEqual(self.trip.status, "IN_PROGRESS")
        self.assertEqual(trip2.status, "IN_PROGRESS")

        # First user requests completion
        self.client.logout()
        self.client.login(username="testuser", password="testpass")
        response = self.client.post(reverse("complete_trip"))

        # Verify both trips are automatically completed (majority reached)
        self.trip.refresh_from_db()
        trip2.refresh_from_db()
        self.assertEqual(self.trip.status, "COMPLETED")
        self.assertEqual(trip2.status, "COMPLETED")
        self.assertRedirects(response, reverse("previous_trips"))

    def test_cancel_during_ready_state(self):
        """Test cancellation during matching/ready state affects both users correctly"""
        # Create second user's trip with compatible parameters
        trip2 = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="SEARCHING",
            planned_departure=self.trip.planned_departure,
            desired_companions=1,
            search_radius=200,
        )

        # First user sends match request
        response = self.client.post(
            reverse("send_match_request"), {"trip_id": trip2.id, "action": "send"}
        )
        self.assertTrue(response.json()["success"])

        # Second user accepts match request
        self.client.logout()
        self.client.login(username="testuser2", password="testpass2")
        match = Match.objects.get(trip1=self.trip, trip2=trip2)
        response = self.client.post(
            reverse("handle_match_request"), {"match_id": match.id, "action": "accept"}
        )
        self.assertRedirects(response, reverse("current_trip"))

        # Verify both trips are matched
        self.trip.refresh_from_db()
        trip2.refresh_from_db()
        self.assertEqual(self.trip.status, "MATCHED")
        self.assertEqual(trip2.status, "MATCHED")

        # First user marks ready
        self.client.logout()
        self.client.login(username="testuser", password="testpass")
        response = self.client.post(reverse("start_trip"))
        self.assertRedirects(response, reverse("current_trip"))

        # Second user cancels their trip
        self.client.logout()
        self.client.login(username="testuser2", password="testpass2")
        response = self.client.post(reverse("cancel_trip"))
        self.assertRedirects(response, reverse("home"))

        # Verify trip states: first user back to searching, second user cancelled
        self.trip.refresh_from_db()
        trip2.refresh_from_db()
        self.assertEqual(self.trip.status, "SEARCHING")
        self.assertEqual(trip2.status, "CANCELLED")

        # Verify match is now declined
        match.refresh_from_db()
        self.assertEqual(match.status, "DECLINED")

        # Verify companion counts reset
        self.assertEqual(self.trip.accepted_companions_count, 0)
        self.assertEqual(trip2.accepted_companions_count, 0)

    def test_user_location_str(self):
        expected = "testuser's location (40.7128, -74.006)"
        self.assertEqual(str(self.location), expected)

    def test_trip_str(self):
        expected = f"testuser's trip on {self.trip.created_at.date()}"
        self.assertEqual(str(self.trip), expected)

    def test_match_str(self):
        matched_trip = Trip.objects.create(
            user=self.user2,
            start_latitude="40.7129",
            start_longitude="-74.0061",
            dest_latitude="40.7581",
            dest_longitude="-73.9856",
            status="IN_PROGRESS",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
            desired_companions=1,
            search_radius=200,
            completion_requested=True,  # Other user already voted
        )

        match = Match.objects.create(
            trip1=self.trip, trip2=matched_trip, status="ACCEPTED"
        )

        expected = "Match between testuser and testuser2"
        self.assertEqual(str(match), expected)

    @patch("locations.views.pusher_client")
    def test_resolve_panic_user_location_not_found(self, mock_pusher):
        # Use non-existent username
        self.user.userprofile.is_verified = True
        self.user.userprofile.is_emergency_support = True
        self.location.delete()
        self.user.save()

        self.client.logout()
        self.client.login(username="testuser", password="testpass")

        response = self.client.post(reverse("resolve_panic", args=["testuser"]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error"], "UserLocation matching query does not exist."
        )
        mock_pusher.trigger.assert_not_called()

    @patch("locations.views.pusher_client")
    def test_resolve_panic_success(self, mock_pusher):
        # Setup panic state
        self.location.panic = True
        self.location.panic_message = "Help!"
        self.location.save()

        # Setup trip status
        self.trip.status = "IN_PROGRESS"
        self.trip.chatroom = ChatRoom.objects.create(name="Test Chatroom")
        self.trip.save()

        self.user2.userprofile.is_emergency_support = True
        self.user2.save()
        self.client.login(username="testuser2", password="testpass2")

        response = self.client.post(reverse("resolve_panic", args=[self.user.username]))

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["message"], "Panic mode deactivated.")

        # Check location updated
        self.location.refresh_from_db()
        self.assertFalse(self.location.panic)
        self.assertIsNone(self.location.panic_message)

        outLog = f"Emergency support has resolved {self.user.username}'s panic request."

        # Verify pusher calls
        mock_pusher.trigger.assert_has_calls(
            [
                call(
                    "emergency-channel",
                    "panic-resolve",
                    {"username": self.user.username},
                ),
                call(
                    f"chat-{self.trip.chatroom.id}",
                    "message-event",
                    {
                        "message": outLog,
                        "type": "system",
                    },
                ),
            ]
        )

    @patch("locations.views.pusher_client")
    def test_resolve_panic_location_not_found(self, mock_pusher):
        self.user.userprofile.is_emergency_support = True
        self.location.delete()
        self.user.save()

        response = self.client.post(reverse("resolve_panic", args=["testuser"]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error"], "UserLocation matching query does not exist."
        )
        mock_pusher.trigger.assert_not_called()

    @patch("locations.views.pusher_client")
    def test_trigger_panic_success(self, mock_pusher):
        self.trip.status = "IN_PROGRESS"
        self.trip.chatroom = ChatRoom.objects.create(name="Test Chatroom")
        self.trip.save()

        response = self.client.post(
            reverse("trigger_panic"), {"initial_message": "Help!"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        self.location.refresh_from_db()
        self.assertTrue(self.location.panic)
        self.assertEqual(self.location.panic_message, "Help!")

        mock_pusher.trigger.assert_has_calls(
            [
                call(
                    "emergency-channel",
                    "panic-create",
                    {
                        "locations": [
                            {
                                "id": self.location.id,
                                "username": self.user.username,
                                "panic_message": "Help!",
                                "latitude": float(self.location.latitude),
                                "longitude": float(self.location.longitude),
                            }
                        ],
                        "active_users": 1,
                        "panic_users": 1,
                    },
                ),
                call(
                    f"chat-{self.trip.chatroom.id}",
                    "message-event",
                    {
                        "message": f"{self.user.username} has triggered panic mode.",
                        "type": "ems_system",
                    },
                ),
                call(
                    f"chat-{self.trip.chatroom.id}",
                    "message-event",
                    {
                        "message": self.location.panic_message,
                        "username": self.user.username,
                        "type": "ems_panic_message",
                    },
                ),
            ]
        )

    @patch("locations.views.pusher_client")
    def test_trigger_panic_user_location_not_found(self, mock_pusher):
        self.location.delete()
        response = self.client.post(
            reverse("trigger_panic"), {"initial_message": "Help!"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error"], "UserLocation matching query does not exist."
        )
        mock_pusher.trigger.assert_not_called()

    @patch("locations.views.pusher_client")
    def test_send_ems_message(self, mock_pusher):
        chatroom = ChatRoom.objects.create(name="Test Chatroom")
        system_message = "Emergency alert!"
        panic_message = "Help!"

        send_ems_message(chatroom, system_message, panic_message, self.user)

        self.assertEqual(Message.objects.count(), 2)
        system_msg = Message.objects.get(message_type="EMS_SYSTEM")
        panic_msg = Message.objects.get(message_type="EMS_PANIC_MESSAGE")

        self.assertEqual(system_msg.decrypt_message(), system_message)
        self.assertEqual(system_msg.chat_room, chatroom)
        self.assertEqual(panic_msg.decrypt_message(), panic_message)
        self.assertEqual(panic_msg.chat_room, chatroom)
        self.assertEqual(panic_msg.user, self.user)

        mock_pusher.trigger.assert_has_calls(
            [
                call(
                    f"chat-{chatroom.id}",
                    "message-event",
                    {"message": system_message, "type": "ems_system"},
                ),
                call(
                    f"chat-{chatroom.id}",
                    "message-event",
                    {
                        "message": panic_message,
                        "username": self.user.username,
                        "type": "ems_panic_message",
                    },
                ),
            ]
        )

    def test_reschedule_nonexistent_trip(self):
        """Test rescheduling when trip doesn't exist"""
        self.trip.delete()
        response = self.client.get(reverse("reschedule_trip"))
        self.assertRedirects(response, reverse("home"))


class TripFiltersTest(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="pass1")
        self.user1.userprofile.is_verified = True
        self.user1.userprofile.save()

        self.user2 = User.objects.create_user(username="user2", password="pass2")
        self.user2.userprofile.is_verified = True
        self.user2.userprofile.save()
        # Create base trips
        self.trip1 = Trip.objects.create(
            user=self.user1,
            start_latitude=40.7128,
            start_longitude=-74.0060,
            dest_latitude=40.7580,
            dest_longitude=-73.9855,
            status="MATCHED",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
        )
        self.trip2 = Trip.objects.create(
            user=self.user2,
            start_latitude=40.7129,
            start_longitude=-74.0061,
            dest_latitude=40.7581,
            dest_longitude=-73.9856,
            status="MATCHED",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
        )

    def test_sub_filter(self):
        """Test the subtraction filter"""
        self.assertEqual(sub(5, 3), 2)
        self.assertEqual(sub(10, 5), 5)
        self.assertEqual(sub(0, 0), 0)

    def test_all_matches_filter(self):
        """Test filter returns all matches for a trip"""
        Match.objects.create(trip1=self.trip1, trip2=self.trip2, status="ACCEPTED")
        matches = all_matches(self.trip1)
        self.assertEqual(matches.count(), 1)

    def test_completion_votes_count(self):
        """Test counting completion votes"""
        Match.objects.create(trip1=self.trip1, trip2=self.trip2, status="ACCEPTED")
        self.trip1.completion_requested = True
        self.trip1.save()
        self.trip2.completion_requested = True
        self.trip2.save()

        votes = completion_votes_count(self.trip1)
        self.assertEqual(votes, 2)  # Both trips requested completion

    def test_has_pending_match(self):
        """Test checking for pending matches between trips"""
        Match.objects.create(trip1=self.trip1, trip2=self.trip2, status="PENDING")
        self.assertTrue(has_pending_match(self.trip1, self.trip2))

    def test_total_group_members(self):
        """Test counting total group members including all accepted matches"""
        # Create additional user and trip for testing larger groups
        user3 = User.objects.create_user(username="user3", password="pass3")
        user3.userprofile.is_verified = True
        user3.userprofile.save()

        trip3 = Trip.objects.create(
            user=user3,
            start_latitude=40.7130,
            start_longitude=-74.0062,
            dest_latitude=40.7582,
            dest_longitude=-73.9857,
            status="MATCHED",
            planned_departure=make_aware(datetime.now() + timedelta(hours=1)),
        )

        # Create accepted matches between trips
        Match.objects.create(trip1=self.trip1, trip2=self.trip2, status="ACCEPTED")
        Match.objects.create(trip1=self.trip2, trip2=trip3, status="ACCEPTED")

        # Test count for each trip
        self.assertEqual(total_group_members(self.trip1), 2)  # Connected to trip2
        self.assertEqual(
            total_group_members(self.trip2), 3
        )  # Connected to trip1 and trip3
        self.assertEqual(total_group_members(trip3), 2)  # Connected to trip2
