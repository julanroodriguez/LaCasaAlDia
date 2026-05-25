from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    ROLE_CLIENT = "cliente"
    ROLE_OV = "ov"
    ROLE_LAV = "lavanderia"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_CLIENT, "Cliente"),
        (ROLE_OV, "Oficios varios"),
        (ROLE_LAV, "Lavanderia"),
        (ROLE_ADMIN, "Administrador"),
    ]
    STATUS_PENDING = "pendiente"
    STATUS_APPROVED = "aprobado"
    STATUS_REJECTED = "rechazado"
    STATUS_BLOCKED = "bloqueado"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_APPROVED, "Aprobado"),
        (STATUS_REJECTED, "Rechazado"),
        (STATUS_BLOCKED, "Bloqueado"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=30, blank=True)
    document_id = models.CharField(max_length=40, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    neighborhood = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    verified_at = models.DateTimeField(null=True, blank=True)
    provides_home_service = models.BooleanField(default=True)
    store_address = models.CharField(max_length=160, blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class ProviderService(models.Model):
    CATEGORY_OV = "oficios"
    CATEGORY_LAUNDRY = "lavanderia"
    CATEGORY_CHOICES = [(CATEGORY_OV, "Oficios varios"), (CATEGORY_LAUNDRY, "Lavanderia")]

    provider = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="services")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=60)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.provider}"


class PaymentMethod(models.Model):
    TYPE_CHOICES = [("tarjeta", "Tarjeta"), ("pse", "PSE"), ("efectivo", "Efectivo")]

    client = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="payment_methods")
    method_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    label = models.CharField(max_length=80)
    last_four = models.CharField(max_length=4, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label


class Reservation(models.Model):
    STATUS_PENDING = "pendiente"
    STATUS_ACCEPTED = "aceptado"
    STATUS_IN_PROGRESS = "prestando"
    STATUS_REJECTED = "rechazado"
    STATUS_FINISHED = "finalizado"
    STATUS_CANCELLED = "cancelado"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_ACCEPTED, "Aceptado"),
        (STATUS_IN_PROGRESS, "Prestando servicio"),
        (STATUS_REJECTED, "Rechazado"),
        (STATUS_FINISHED, "Finalizado"),
        (STATUS_CANCELLED, "Cancelado"),
    ]
    MODALITY_HOME = "domicilio"
    MODALITY_STORE = "punto_fisico"
    MODALITY_CHOICES = [(MODALITY_HOME, "Domicilio"), (MODALITY_STORE, "Punto fisico")]

    client = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="client_reservations")
    provider = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="provider_reservations")
    service = models.ForeignKey(ProviderService, on_delete=models.PROTECT)
    scheduled_for = models.DateTimeField()
    modality = models.CharField(max_length=20, choices=MODALITY_CHOICES, default=MODALITY_HOME)
    address = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reserva #{self.pk} {self.service.name}"


class Offer(models.Model):
    TYPE_OV = "oficios"
    TYPE_LAUNDRY = "lavanderia"
    TYPE_CHOICES = [(TYPE_OV, "Oficios varios"), (TYPE_LAUNDRY, "Lavanderia")]
    STATUS_OPEN = "abierta"
    STATUS_ASSIGNED = "asignada"
    STATUS_CLOSED = "cerrada"
    STATUS_REMOVED = "eliminada"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Abierta"),
        (STATUS_ASSIGNED, "Asignada"),
        (STATUS_CLOSED, "Cerrada"),
        (STATUS_REMOVED, "Eliminada"),
    ]

    client = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="offers")
    title = models.CharField(max_length=120)
    service_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    address = models.CharField(max_length=160)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    selected_application = models.OneToOneField(
        "OfferApplication", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class OfferApplication(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="applications")
    provider = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="applications")
    message = models.TextField(blank=True)
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("offer", "provider")


class Payment(models.Model):
    STATUS_PENDING = "pendiente"
    STATUS_PAID = "pagado"
    STATUS_FAILED = "fallido"
    STATUS_CHOICES = [(STATUS_PENDING, "Pendiente"), (STATUS_PAID, "Pagado"), (STATUS_FAILED, "Fallido")]

    client = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="payments")
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PAID)
    transaction_code = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Rating(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="ratings")
    from_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="ratings_given")
    to_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="ratings_received")
    stars = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reservation", "from_profile", "to_profile")


class Conversation(models.Model):
    participants = models.ManyToManyField(Profile, related_name="conversations")
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.SET_NULL)
    offer = models.ForeignKey(Offer, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Sanction(models.Model):
    ACTION_BLOCK = "bloqueo"
    ACTION_SUSPEND = "suspension"
    ACTION_CHOICES = [(ACTION_BLOCK, "Bloqueo"), (ACTION_SUSPEND, "Suspension")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sanctions")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField()
    days = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.days and not self.ends_at:
            self.ends_at = timezone.now() + timezone.timedelta(days=self.days)
        super().save(*args, **kwargs)


class Dispute(models.Model):
    STATUS_OPEN = "abierta"
    STATUS_RESOLVED = "resuelta"
    STATUS_CHOICES = [(STATUS_OPEN, "Abierta"), (STATUS_RESOLVED, "Resuelta")]

    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="disputes")
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.CharField(max_length=120)
    description = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
