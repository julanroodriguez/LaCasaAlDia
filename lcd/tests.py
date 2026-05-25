import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from .models import Offer, OfferApplication, Profile, Reservation


class OfferAssignmentFlowTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="cliente@test.com",
            email="cliente@test.com",
            password="pass",
            first_name="Cliente",
        )
        self.provider_user = User.objects.create_user(
            username="oficios@test.com",
            email="oficios@test.com",
            password="pass",
            first_name="Oficios",
        )
        self.client_profile = Profile.objects.create(
            user=self.client_user,
            role=Profile.ROLE_CLIENT,
            status=Profile.STATUS_APPROVED,
            address="Calle 1",
        )
        self.provider_profile = Profile.objects.create(
            user=self.provider_user,
            role=Profile.ROLE_OV,
            status=Profile.STATUS_APPROVED,
        )
        self.offer = Offer.objects.create(
            client=self.client_profile,
            title="Aseo apartamento",
            service_type=Offer.TYPE_OV,
            description="Limpieza general",
            address="Calle 1",
            budget=Decimal("80000"),
            scheduled_for=timezone.now() + timezone.timedelta(days=1),
        )
        self.application = OfferApplication.objects.create(
            offer=self.offer,
            provider=self.provider_profile,
            message="Disponible",
            proposed_price=Decimal("75000"),
        )

    def test_assigned_offer_moves_to_agenda_for_client_and_provider(self):
        browser = Client()
        browser.force_login(self.client_user)

        response = browser.post(
            f"/api/offers/{self.offer.id}/choose/{self.application.id}/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.status, Offer.STATUS_ASSIGNED)
        reservation = Reservation.objects.get(client=self.client_profile, provider=self.provider_profile)
        self.assertEqual(reservation.status, Reservation.STATUS_ACCEPTED)

        client_bootstrap = browser.get("/api/bootstrap/").json()
        self.assertEqual(client_bootstrap["offers"], [])
        self.assertEqual(len(client_bootstrap["reservations"]), 1)
        self.assertEqual(client_bootstrap["reservations"][0]["status"], Reservation.STATUS_ACCEPTED)

        browser.force_login(self.provider_user)
        provider_bootstrap = browser.get("/api/bootstrap/").json()
        self.assertEqual(provider_bootstrap["offers"], [])
        self.assertEqual(len(provider_bootstrap["reservations"]), 1)
        self.assertEqual(provider_bootstrap["reservations"][0]["status"], Reservation.STATUS_ACCEPTED)

    def test_provider_payment_count_updates_when_client_pays(self):
        browser = Client()
        browser.force_login(self.client_user)
        choose_response = browser.post(
            f"/api/offers/{self.offer.id}/choose/{self.application.id}/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(choose_response.status_code, 200)
        reservation_id = choose_response.json()["reservation"]["id"]

        pay_response = browser.post(
            "/api/payments/",
            data=json.dumps(
                {
                    "reservation_id": reservation_id,
                    "card_name": "Cliente Demo",
                    "card_number": "4111111111111111",
                    "expires": "12/30",
                    "cvv": "123",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(pay_response.status_code, 200)
        self.assertEqual(len(browser.get("/api/bootstrap/").json()["payments"]), 1)

        browser.force_login(self.provider_user)
        provider_bootstrap = browser.get("/api/bootstrap/").json()
        self.assertEqual(len(provider_bootstrap["payments"]), 1)
        self.assertEqual(provider_bootstrap["payments"][0]["reservation_id"], reservation_id)
