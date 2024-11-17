# from django.test import TestCase

# Create your tests here.

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Trip, Match, UserLocation
from datetime import datetime, timedelta
from django.utils.timezone import make_aware


class LocationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user2 = User.objects.create_user(
            username="testuser2", password="testpass2"
        )
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
            "desired_companions": 1,
            "search_radius": 200,
        }
        response = self.client.post(reverse("create_trip"), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Trip.objects.filter(user=self.user).exists())

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
        self.assertContains(response, "No active trip found")

    def test_get_trip_locations_no_trip(self):
        """Test get_trip_locations when no trip exists"""
        self.trip.delete()
        response = self.client.get(reverse("get_trip_locations"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])

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
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])

    def test_cancel_nonexistent_trip(self):
        """Test cancelling when no active trip exists"""
        self.trip.delete()
        response = self.client.post(reverse("cancel_trip"))
        self.assertEqual(response.status_code, 302)
