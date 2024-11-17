from django.test import TestCase, Client
from django.contrib.auth.models import User
from chat.models import ChatRoom, Message
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from locations.models import Trip, Match  # Add these imports
import json


class ChatModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.chat_room = ChatRoom.objects.create(
            name="Test Room", description="Test Description"
        )
        self.chat_room.users.add(self.user)

    def test_chat_room_creation(self):
        self.assertEqual(self.chat_room.name, "Test Room")
        self.assertEqual(self.chat_room.description, "Test Description")
        self.assertTrue(self.chat_room.users.filter(id=self.user.id).exists())

    def test_chat_room_str(self):
        chat_room = ChatRoom.objects.create(name="Test Room 2")
        self.assertEqual(str(chat_room), "Test Room 2")

    def test_message_str(self):
        message = Message.objects.create(
            chat_room=self.chat_room, user=self.user, message="Test message"
        )
        expected_str = f"{self.user.username}'s message on {self.chat_room.name}"
        self.assertEqual(str(message), expected_str)

    def test_message_encryption(self):
        message = Message.objects.create(
            chat_room=self.chat_room, user=self.user, message="Test message"
        )
        # Original message should be encrypted
        self.assertNotEqual(message.message, "Test message")
        # Decrypted message should match original
        self.assertEqual(message.decrypt_message(), "Test message")

    def test_system_message_no_encryption(self):
        system_message = Message.objects.create(
            chat_room=self.chat_room, message="System alert", message_type="SYSTEM"
        )
        # System messages should not be encrypted
        self.assertEqual(system_message.message, "System alert")
        self.assertEqual(system_message.decrypt_message(), "System alert")


class ChatViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create two users
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.other_user = User.objects.create_user(
            username="otheruser", password="testpass"
        )

        # Create chat room
        self.chat_room = ChatRoom.objects.create(name="Test Room")
        self.chat_room.users.add(self.user, self.other_user)

        # Create trips for both users
        self.trip1 = Trip.objects.create(
            user=self.user,
            start_latitude=40.7128,
            start_longitude=-74.0060,
            dest_latitude=40.7580,
            dest_longitude=-73.9855,
            status="IN_PROGRESS",
            planned_departure=timezone.now() + timedelta(hours=1),
            chatroom=self.chat_room,
        )

        self.trip2 = Trip.objects.create(
            user=self.other_user,
            start_latitude=40.7128,
            start_longitude=-74.0060,
            dest_latitude=40.7580,
            dest_longitude=-73.9855,
            status="IN_PROGRESS",
            planned_departure=timezone.now() + timedelta(hours=1),
            chatroom=self.chat_room,
        )

        # Create match between the trips
        self.match = Match.objects.create(
            trip1=self.trip1,
            trip2=self.trip2,
            status="ACCEPTED",
            chatroom=self.chat_room,
        )

        self.client.login(username="testuser", password="testpass")

    def test_chat_room_view(self):
        response = self.client.get(
            reverse("chat_room", kwargs={"pk": self.chat_room.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/chat_room_modal.html")

    def test_send_message_invalid_request(self):
        response = self.client.post(reverse("send_message"))
        self.assertEqual(response.status_code, 400)  # Bad Request is correct response

    def test_send_message(self):
        data = {"chat_room": self.chat_room.id, "message": "Test message"}
        response = self.client.post(
            reverse("send_message"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Message.objects.filter(chat_room=self.chat_room).exists())

    def test_unauthorized_chat_access(self):
        # Create another user not in the chat room
        User.objects.create_user(username="other", password="testpass")
        self.client.login(username="other", password="testpass")

        response = self.client.get(
            reverse("chat_room", kwargs={"pk": self.chat_room.pk})
        )
        self.assertEqual(response.status_code, 302)  # Should redirect

    def test_invalid_chat_room_id(self):
        response = self.client.get(reverse("chat_room", kwargs={"pk": 999}))
        self.assertEqual(response.status_code, 404)

    def test_invalid_chat_room_id_type(self):
        response = self.client.get(reverse("chat_room", kwargs={"pk": "asd"}))
        self.assertEqual(response.status_code, 400)

    def test_chat_room_view_redirect_current_trip(self):
        # Change trip status to make it invalid for current chat
        self.trip1.status = "SEARCHING"
        self.trip1.save()
        self.trip2.status = "SEARCHING"
        self.trip2.save()

        response = self.client.get(
            reverse("chat_room", kwargs={"pk": self.chat_room.pk})
        )
        self.assertRedirects(response, reverse("current_trip"))

    def test_chat_room_view_redirect_previous_trips(self):
        # Set both trips to IN_PROGRESS (not COMPLETED/CANCELLED)
        self.trip1.status = "IN_PROGRESS"
        self.trip1.save()
        self.trip2.status = "IN_PROGRESS"
        self.trip2.save()

        # Try to access with archive parameter when trips aren't completed
        response = self.client.get(
            reverse("chat_room", kwargs={"pk": self.chat_room.pk}) + "?archive=true"
        )
        self.assertRedirects(response, reverse("previous_trips"))

    def test_chat_room_view_redirect_completed_trip(self):
        # Now test valid archived access
        self.trip1.status = "COMPLETED"
        self.trip1.save()
        self.trip2.status = "COMPLETED"
        self.trip2.save()

        response = self.client.get(
            reverse("chat_room", kwargs={"pk": self.chat_room.pk}) + "?archive=true"
        )
        self.assertEqual(response.status_code, 200)

    def test_send_message_invalid_api_request(self):
        response = self.client.get(reverse("send_message"))
        self.assertEqual(response.status_code, 405)  # Bad Request is correct response
