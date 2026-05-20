from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from lcd.models import (
    Conversation,
    Notification,
    Offer,
    OfferApplication,
    Payment,
    PaymentMethod,
    Profile,
    ProviderService,
    Reservation,
)


class Command(BaseCommand):
    help = "Carga datos demo para La Casa al Dia."

    def handle(self, *args, **options):
        admin = self.user("admin@lcd.com", "Admin", "LCD", "admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        admin_profile = self.profile(admin, Profile.ROLE_ADMIN, Profile.STATUS_APPROVED, city="Bogota")

        client = self.user("cliente@lcd.com", "Mariana", "Lopez", "cliente123")
        client_profile = self.profile(
            client,
            Profile.ROLE_CLIENT,
            Profile.STATUS_APPROVED,
            city="Bogota",
            neighborhood="Chapinero",
            address="Calle 45 # 13-20",
            phone="3001234567",
        )

        ov = self.user("oficios@lcd.com", "Diego", "Gomez", "oficios123")
        ov_profile = self.profile(
            ov,
            Profile.ROLE_OV,
            Profile.STATUS_APPROVED,
            city="Bogota",
            neighborhood="Teusaquillo",
            address="Carrera 19 # 50-10",
            phone="3112223344",
            bio="Servicios de aseo, cocina basica, planchado y limpieza general.",
        )

        lav = self.user("lavanderia@lcd.com", "Oscar", "Briceño", "lav123")
        lav_profile = self.profile(
            lav,
            Profile.ROLE_LAV,
            Profile.STATUS_APPROVED,
            city="Bogota",
            neighborhood="Cedritos",
            address="Avenida 9 # 140-25",
            phone="3224445566",
            bio="Lavanderia aliada con recoleccion y entrega a domicilio.",
            store_address="Local 12, Centro Comercial Cedritos",
            provides_home_service=True,
        )

        aseo = self.service(ov_profile, "oficios", "Limpieza general", 65000, 180, "Aseo profundo para apartamento o casa.")
        planchado = self.service(ov_profile, "oficios", "Planchado por horas", 35000, 120, "Planchado y organizacion de prendas.")
        lavado = self.service(lav_profile, "lavanderia", "Lavado a domicilio", 42000, 1440, "Recoleccion, lavado y entrega.")
        self.service(lav_profile, "lavanderia", "Lavado en punto fisico", 30000, 1440, "Entrega y recogida en lavanderia.")

        method, _ = PaymentMethod.objects.get_or_create(
            client=client_profile,
            label="Visa terminada en 1234",
            defaults={"method_type": "tarjeta", "last_four": "1234"},
        )
        reservation, _ = Reservation.objects.get_or_create(
            client=client_profile,
            provider=ov_profile,
            service=aseo,
            scheduled_for=timezone.now() + timezone.timedelta(days=2),
            defaults={
                "address": client_profile.address,
                "notes": "Limpieza de sala, cocina y banos.",
                "status": Reservation.STATUS_ACCEPTED,
                "total": aseo.price,
            },
        )
        Payment.objects.get_or_create(
            client=client_profile,
            reservation=reservation,
            defaults={"method": method, "amount": reservation.total, "status": Payment.STATUS_PAID, "transaction_code": "LCD-DEMO-001"},
        )
        conv, _ = Conversation.objects.get_or_create(reservation=reservation)
        conv.participants.set([client_profile, ov_profile])

        offer, _ = Offer.objects.get_or_create(
            client=client_profile,
            title="Aseo y cocina para reunion familiar",
            defaults={
                "service_type": Offer.TYPE_OV,
                "description": "Necesito apoyo con limpieza previa y preparacion sencilla de alimentos.",
                "address": client_profile.address,
                "budget": Decimal("90000"),
                "scheduled_for": timezone.now() + timezone.timedelta(days=5),
            },
        )
        OfferApplication.objects.get_or_create(offer=offer, provider=ov_profile, defaults={"message": "Tengo disponibilidad y experiencia.", "proposed_price": Decimal("85000")})

        for target, title in [
            (client_profile, "Bienvenida a La Casa al Dia"),
            (ov_profile, "Tu perfil esta aprobado"),
            (lav_profile, "Tu lavanderia esta lista para recibir solicitudes"),
            (admin_profile, "Panel administrativo preparado"),
        ]:
            Notification.objects.get_or_create(recipient=target, title=title, defaults={"body": "Dato demo creado correctamente."})

        self.stdout.write(self.style.SUCCESS("Datos demo listos."))
        self.stdout.write("Usuarios: admin@lcd.com/admin123, cliente@lcd.com/cliente123, oficios@lcd.com/oficios123, lavanderia@lcd.com/lav123")

    def user(self, email, first_name, last_name, password):
        user, created = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": first_name, "last_name": last_name})
        if created:
            user.set_password(password)
            user.save()
        return user

    def profile(self, user, role, status, **kwargs):
        profile, _ = Profile.objects.update_or_create(
            user=user,
            defaults={"role": role, "status": status, **kwargs},
        )
        return profile

    def service(self, provider, category, name, price, duration, description):
        service, _ = ProviderService.objects.update_or_create(
            provider=provider,
            name=name,
            defaults={"category": category, "price": Decimal(str(price)), "duration_minutes": duration, "description": description, "active": True},
        )
        return service
