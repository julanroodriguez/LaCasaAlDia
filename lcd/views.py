import csv
import json
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Conversation,
    Dispute,
    Message,
    Notification,
    Offer,
    OfferApplication,
    Payment,
    PaymentMethod,
    Profile,
    ProviderService,
    Rating,
    Reservation,
    Sanction,
)


def index(request):
    return render(request, "index.html")


def payload(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def ok(data=None, status=200):
    return JsonResponse(data or {}, status=status)


def error(message, status=400):
    return ok({"error": message}, status)


def profile_or_none(user):
    return getattr(user, "profile", None) if user.is_authenticated else None


def require_profile(request):
    profile = profile_or_none(request.user)
    if not profile:
        return None, error("Debes iniciar sesion.", 401)
    if profile.status == Profile.STATUS_BLOCKED:
        return None, error("Tu cuenta esta bloqueada.", 403)
    return profile, None


def is_admin(profile):
    return profile and (profile.role == Profile.ROLE_ADMIN or profile.user.is_staff)


def money(value):
    return float(value or 0)


def dt(value):
    if not value:
        return None
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed and timezone.is_naive(parsed):
            return timezone.make_aware(parsed)
        return parsed
    return value


def serialize_profile(profile):
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "username": profile.user.username,
        "full_name": profile.user.get_full_name() or profile.user.username,
        "email": profile.user.email,
        "role": profile.role,
        "phone": profile.phone,
        "document_id": profile.document_id,
        "city": profile.city,
        "neighborhood": profile.neighborhood,
        "address": profile.address,
        "bio": profile.bio,
        "status": profile.status,
        "photo_url": profile.photo_url,
        "store_address": profile.store_address,
        "provides_home_service": profile.provides_home_service,
        "average_rating": money(profile.average_rating),
        "rating_count": profile.rating_count,
        "created_at": profile.created_at.isoformat(),
    }


def serialize_service(service):
    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "provider_name": service.provider.user.get_full_name() or service.provider.user.username,
        "category": service.category,
        "name": service.name,
        "description": service.description,
        "price": money(service.price),
        "duration_minutes": service.duration_minutes,
        "active": service.active,
    }


def serialize_reservation(reservation):
    return {
        "id": reservation.id,
        "client": serialize_profile(reservation.client),
        "provider": serialize_profile(reservation.provider),
        "service": serialize_service(reservation.service),
        "scheduled_for": reservation.scheduled_for.isoformat(),
        "modality": reservation.modality,
        "address": reservation.address,
        "notes": reservation.notes,
        "status": reservation.status,
        "total": money(reservation.total),
        "created_at": reservation.created_at.isoformat(),
    }


def serialize_offer(offer, with_apps=False):
    data = {
        "id": offer.id,
        "client": serialize_profile(offer.client),
        "title": offer.title,
        "service_type": offer.service_type,
        "description": offer.description,
        "address": offer.address,
        "budget": money(offer.budget),
        "scheduled_for": offer.scheduled_for.isoformat() if offer.scheduled_for else "",
        "status": offer.status,
        "selected_application_id": offer.selected_application_id,
        "created_at": offer.created_at.isoformat(),
    }
    if with_apps:
        data["applications"] = [
            {
                "id": app.id,
                "provider": serialize_profile(app.provider),
                "message": app.message,
                "proposed_price": money(app.proposed_price),
                "created_at": app.created_at.isoformat(),
            }
            for app in offer.applications.select_related("provider__user")
        ]
    return data


def notify(profile, title, body=""):
    Notification.objects.create(recipient=profile, title=title, body=body)


@csrf_exempt
def session_view(request):
    profile = profile_or_none(request.user)
    return ok({"authenticated": bool(profile), "profile": serialize_profile(profile) if profile else None})


@csrf_exempt
def register(request):
    data = payload(request)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or Profile.ROLE_CLIENT
    if role not in dict(Profile.ROLE_CHOICES):
        return error("Rol invalido.")
    if not email or not password:
        return error("Email y contrasena son obligatorios.")
    if User.objects.filter(username=email).exists():
        return error("Este correo ya esta registrado.")

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
    )
    profile = Profile.objects.create(
        user=user,
        role=role,
        phone=data.get("phone", ""),
        document_id=data.get("document_id", ""),
        birth_date=data.get("birth_date") or None,
        city=data.get("city", ""),
        neighborhood=data.get("neighborhood", ""),
        address=data.get("address", ""),
        bio=data.get("bio", ""),
        store_address=data.get("store_address", ""),
        provides_home_service=bool(data.get("provides_home_service", True)),
        status=Profile.STATUS_APPROVED if role == Profile.ROLE_CLIENT else Profile.STATUS_PENDING,
    )
    if role == Profile.ROLE_ADMIN:
        profile.status = Profile.STATUS_APPROVED
        profile.save(update_fields=["status"])
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
    login(request, user)
    notify(profile, "Registro creado", "Tu cuenta quedo guardada en La Casa al Dia.")
    return ok({"profile": serialize_profile(profile)}, 201)


@csrf_exempt
def login_view(request):
    data = payload(request)
    email = (data.get("email") or "").strip().lower()
    user = authenticate(request, username=email, password=data.get("password", ""))
    if not user:
        return error("Credenciales incorrectas.", 401)
    profile = profile_or_none(user)
    if not profile:
        return error("El usuario no tiene perfil asociado.", 403)
    if profile.status == Profile.STATUS_BLOCKED:
        return error("La cuenta esta bloqueada.", 403)
    login(request, user)
    return ok({"profile": serialize_profile(profile)})


@csrf_exempt
def logout_view(request):
    logout(request)
    return ok({"message": "Sesion cerrada."})


@csrf_exempt
def bootstrap(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    reservations_q = Reservation.objects.select_related("client__user", "provider__user", "service")
    if not is_admin(profile):
        reservations_q = reservations_q.filter(Q(client=profile) | Q(provider=profile))
    offers_q = Offer.objects.select_related("client__user").prefetch_related("applications__provider__user")
    if profile.role == Profile.ROLE_CLIENT:
        offers_q = offers_q.filter(client=profile)
    elif profile.role in [Profile.ROLE_OV, Profile.ROLE_LAV]:
        service_type = Offer.TYPE_OV if profile.role == Profile.ROLE_OV else Offer.TYPE_LAUNDRY
        offers_q = offers_q.filter(Q(service_type=service_type, status=Offer.STATUS_OPEN) | Q(applications__provider=profile)).distinct()
    return ok(
        {
            "profile": serialize_profile(profile),
            "providers": [serialize_profile(p) for p in Profile.objects.filter(role__in=[Profile.ROLE_OV, Profile.ROLE_LAV])],
            "services": [serialize_service(s) for s in ProviderService.objects.select_related("provider__user").filter(active=True)],
            "reservations": [serialize_reservation(r) for r in reservations_q.order_by("-scheduled_for")[:100]],
            "offers": [serialize_offer(o, True) for o in offers_q.order_by("-created_at")[:100]],
            "payments": [
                {
                    "id": p.id,
                    "amount": money(p.amount),
                    "status": p.status,
                    "transaction_code": p.transaction_code,
                    "created_at": p.created_at.isoformat(),
                    "reservation_id": p.reservation_id,
                }
                for p in Payment.objects.filter(client=profile).order_by("-created_at")[:50]
            ],
            "notifications": [
                {"id": n.id, "title": n.title, "body": n.body, "read": n.read, "created_at": n.created_at.isoformat()}
                for n in profile.notifications.order_by("-created_at")[:50]
            ],
        }
    )


@csrf_exempt
def profile_view(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    data = payload(request)
    user = profile.user
    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.email = data.get("email", user.email)
    user.save()
    editable = ["phone", "city", "neighborhood", "address", "bio", "store_address", "provides_home_service"]
    for field in editable:
        if field in data:
            setattr(profile, field, data[field])
    profile.save()
    if "services" in data and profile.role in [Profile.ROLE_OV, Profile.ROLE_LAV]:
        profile.services.all().delete()
        for item in data["services"]:
            ProviderService.objects.create(
                provider=profile,
                category=ProviderService.CATEGORY_OV if profile.role == Profile.ROLE_OV else ProviderService.CATEGORY_LAUNDRY,
                name=item.get("name", "Servicio"),
                description=item.get("description", ""),
                price=Decimal(str(item.get("price") or 0)),
                duration_minutes=int(item.get("duration_minutes") or 60),
            )
    return ok({"profile": serialize_profile(profile)})


@csrf_exempt
def providers(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    category = request.GET.get("category")
    qs = Profile.objects.filter(role__in=[Profile.ROLE_OV, Profile.ROLE_LAV], status=Profile.STATUS_APPROVED)
    if category == "oficios":
        qs = qs.filter(role=Profile.ROLE_OV)
    if category == "lavanderia":
        qs = qs.filter(role=Profile.ROLE_LAV)
    return ok({"providers": [serialize_profile(p) for p in qs], "services": [serialize_service(s) for s in ProviderService.objects.filter(provider__in=qs, active=True)]})


@csrf_exempt
def reservations(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if request.method == "GET":
        qs = Reservation.objects.select_related("client__user", "provider__user", "service")
        if not is_admin(profile):
            qs = qs.filter(Q(client=profile) | Q(provider=profile))
        return ok({"reservations": [serialize_reservation(r) for r in qs.order_by("-scheduled_for")]})
    data = payload(request)
    if profile.role != Profile.ROLE_CLIENT:
        return error("Solo los clientes pueden crear reservas.", 403)
    service = get_object_or_404(ProviderService, pk=data.get("service_id"), active=True)
    scheduled_for = dt(data.get("scheduled_for"))
    if not scheduled_for:
        return error("Selecciona fecha y hora validas.")
    if Reservation.objects.filter(provider=service.provider, scheduled_for=scheduled_for, status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_ACCEPTED]).exists():
        return error("El prestador ya tiene una reserva en esa fecha y hora.")
    reservation = Reservation.objects.create(
        client=profile,
        provider=service.provider,
        service=service,
        scheduled_for=scheduled_for,
        modality=data.get("modality") or Reservation.MODALITY_HOME,
        address=data.get("address") or profile.address,
        notes=data.get("notes", ""),
        total=service.price,
    )
    conv = Conversation.objects.create(reservation=reservation)
    conv.participants.set([profile, service.provider])
    notify(service.provider, "Nueva solicitud de servicio", f"{profile.user.get_full_name()} solicito {service.name}.")
    notify(profile, "Reserva creada", "Tu solicitud quedo pendiente de aceptacion.")
    return ok({"reservation": serialize_reservation(reservation)}, 201)


@csrf_exempt
def reservation_status(request, reservation_id):
    profile, denied = require_profile(request)
    if denied:
        return denied
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    data = payload(request)
    new_status = data.get("status")
    if new_status not in dict(Reservation.STATUS_CHOICES):
        return error("Estado invalido.")
    if reservation.provider != profile and reservation.client != profile and not is_admin(profile):
        return error("No tienes permiso para cambiar esta reserva.", 403)
    if profile == reservation.client and new_status not in [Reservation.STATUS_CANCELLED]:
        return error("El cliente solo puede cancelar desde este endpoint.", 403)
    reservation.status = new_status
    reservation.save(update_fields=["status", "updated_at"])
    notify(reservation.client, "Reserva actualizada", f"Tu reserva ahora esta en estado {new_status}.")
    notify(reservation.provider, "Reserva actualizada", f"La reserva ahora esta en estado {new_status}.")
    return ok({"reservation": serialize_reservation(reservation)})


@csrf_exempt
def offers(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if request.method == "GET":
        qs = Offer.objects.select_related("client__user").prefetch_related("applications__provider__user")
        if profile.role == Profile.ROLE_CLIENT:
            qs = qs.filter(client=profile)
        elif profile.role in [Profile.ROLE_OV, Profile.ROLE_LAV]:
            kind = Offer.TYPE_OV if profile.role == Profile.ROLE_OV else Offer.TYPE_LAUNDRY
            qs = qs.filter(service_type=kind, status=Offer.STATUS_OPEN)
        return ok({"offers": [serialize_offer(o, True) for o in qs.order_by("-created_at")]})
    data = payload(request)
    if profile.role != Profile.ROLE_CLIENT:
        return error("Solo los clientes pueden crear ofertas.", 403)
    offer = Offer.objects.create(
        client=profile,
        title=data.get("title", "Oferta de servicio"),
        service_type=data.get("service_type") or Offer.TYPE_OV,
        description=data.get("description", ""),
        address=data.get("address") or profile.address,
        budget=Decimal(str(data.get("budget") or 0)),
        scheduled_for=dt(data.get("scheduled_for")),
    )
    return ok({"offer": serialize_offer(offer, True)}, 201)


@csrf_exempt
def apply_offer(request, offer_id):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if profile.role not in [Profile.ROLE_OV, Profile.ROLE_LAV]:
        return error("Solo trabajadores o lavanderias pueden postularse.", 403)
    offer = get_object_or_404(Offer, pk=offer_id, status=Offer.STATUS_OPEN)
    app, _ = OfferApplication.objects.get_or_create(
        offer=offer,
        provider=profile,
        defaults={"message": payload(request).get("message", ""), "proposed_price": Decimal(str(payload(request).get("proposed_price") or offer.budget))},
    )
    notify(offer.client, "Nueva postulacion", f"{profile.user.get_full_name()} se postulo a tu oferta.")
    return ok({"application": {"id": app.id}})


@csrf_exempt
def choose_application(request, offer_id, application_id):
    profile, denied = require_profile(request)
    if denied:
        return denied
    offer = get_object_or_404(Offer, pk=offer_id, client=profile)
    app = get_object_or_404(OfferApplication, pk=application_id, offer=offer)
    offer.selected_application = app
    offer.status = Offer.STATUS_ASSIGNED
    offer.save(update_fields=["selected_application", "status"])
    notify(app.provider, "Postulacion aceptada", f"Fuiste elegido para la oferta {offer.title}.")
    return ok({"offer": serialize_offer(offer, True)})


@csrf_exempt
def moderate_offer(request, offer_id):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if not is_admin(profile):
        return error("Solo administradores.", 403)
    offer = get_object_or_404(Offer, pk=offer_id)
    data = payload(request)
    offer.status = data.get("status") or Offer.STATUS_REMOVED
    offer.save(update_fields=["status"])
    notify(offer.client, "Oferta moderada", data.get("reason", "Tu oferta fue revisada por administracion."))
    return ok({"offer": serialize_offer(offer, True)})


@csrf_exempt
def payments(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    data = payload(request)
    if request.method == "GET":
        return ok({"payments": [{"id": p.id, "amount": money(p.amount), "status": p.status, "created_at": p.created_at.isoformat()} for p in Payment.objects.filter(client=profile)]})
    if profile.role != Profile.ROLE_CLIENT:
        return error("Solo clientes pueden pagar.", 403)
    reservation = get_object_or_404(Reservation, pk=data.get("reservation_id"), client=profile)
    method, _ = PaymentMethod.objects.get_or_create(
        client=profile,
        label=data.get("method_label", "Pago demo PayU"),
        defaults={"method_type": data.get("method_type", "tarjeta"), "last_four": data.get("last_four", "0000")},
    )
    payment = Payment.objects.create(
        client=profile,
        reservation=reservation,
        method=method,
        amount=reservation.total,
        status=Payment.STATUS_PAID,
        transaction_code=f"LCD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{reservation.id}",
    )
    notify(reservation.provider, "Pago recibido", f"Se registro el pago de la reserva #{reservation.id}.")
    notify(profile, "Pago exitoso", "El pago quedo guardado en tu historial.")
    return ok({"payment": {"id": payment.id, "transaction_code": payment.transaction_code, "amount": money(payment.amount)}})


@csrf_exempt
def ratings(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    data = payload(request)
    reservation = get_object_or_404(Reservation, pk=data.get("reservation_id"))
    if profile not in [reservation.client, reservation.provider]:
        return error("No participas en esta reserva.", 403)
    to_profile = reservation.provider if profile == reservation.client else reservation.client
    rating, _ = Rating.objects.update_or_create(
        reservation=reservation,
        from_profile=profile,
        to_profile=to_profile,
        defaults={"stars": int(data.get("stars") or 5), "comment": data.get("comment", "")},
    )
    stats = Rating.objects.filter(to_profile=to_profile).aggregate(avg=Avg("stars"), count=Count("id"))
    to_profile.average_rating = stats["avg"] or 0
    to_profile.rating_count = stats["count"] or 0
    to_profile.save(update_fields=["average_rating", "rating_count"])
    notify(to_profile, "Nueva calificacion", f"Recibiste {rating.stars} estrellas.")
    return ok({"rating": {"id": rating.id, "stars": rating.stars}})


@csrf_exempt
def messages_view(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    data = payload(request)
    if request.method == "GET":
        conversations = Conversation.objects.filter(participants=profile).prefetch_related("participants__user", "messages")
        return ok(
            {
                "conversations": [
                    {
                        "id": c.id,
                        "participants": [serialize_profile(p) for p in c.participants.all()],
                        "messages": [
                            {"id": m.id, "sender_id": m.sender_id, "body": m.body, "created_at": m.created_at.isoformat()}
                            for m in c.messages.order_by("created_at")
                        ],
                    }
                    for c in conversations
                ]
            }
        )
    conversation = get_object_or_404(Conversation, pk=data.get("conversation_id"), participants=profile)
    msg = Message.objects.create(conversation=conversation, sender=profile, body=data.get("body", ""))
    for participant in conversation.participants.exclude(id=profile.id):
        notify(participant, "Nuevo mensaje", msg.body[:120])
    return ok({"message": {"id": msg.id, "body": msg.body}})


@csrf_exempt
def notifications(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if request.method == "POST":
        profile.notifications.update(read=True)
    return ok({"notifications": [{"id": n.id, "title": n.title, "body": n.body, "read": n.read, "created_at": n.created_at.isoformat()} for n in profile.notifications.order_by("-created_at")]})


@csrf_exempt
def pending_profiles(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if not is_admin(profile):
        return error("Solo administradores.", 403)
    return ok({"profiles": [serialize_profile(p) for p in Profile.objects.filter(status=Profile.STATUS_PENDING).order_by("created_at")]})


@csrf_exempt
def review_profile(request, profile_id):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if not is_admin(profile):
        return error("Solo administradores.", 403)
    target = get_object_or_404(Profile, pk=profile_id)
    data = payload(request)
    target.status = Profile.STATUS_APPROVED if data.get("approved") else Profile.STATUS_REJECTED
    target.verified_at = timezone.now() if data.get("approved") else None
    target.save(update_fields=["status", "verified_at"])
    notify(target, "Revision de perfil", f"Tu perfil fue {target.status}.")
    return ok({"profile": serialize_profile(target)})


@csrf_exempt
def sanction_user(request, user_id):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if not is_admin(profile):
        return error("Solo administradores.", 403)
    data = payload(request)
    user = get_object_or_404(User, pk=user_id)
    sanction = Sanction.objects.create(
        user=user,
        action=data.get("action") or Sanction.ACTION_SUSPEND,
        reason=data.get("reason", ""),
        days=int(data.get("days") or 0),
        created_by=profile.user,
    )
    if sanction.action == Sanction.ACTION_BLOCK:
        user.profile.status = Profile.STATUS_BLOCKED
        user.profile.save(update_fields=["status"])
    notify(user.profile, "Sancion aplicada", sanction.reason)
    return ok({"sanction": {"id": sanction.id}})


@csrf_exempt
def disputes(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    data = payload(request)
    if request.method == "GET":
        qs = Dispute.objects.select_related("created_by__user", "reservation")
        if not is_admin(profile):
            qs = qs.filter(created_by=profile)
        return ok({"disputes": [{"id": d.id, "subject": d.subject, "description": d.description, "response": d.response, "status": d.status} for d in qs]})
    if is_admin(profile) and data.get("dispute_id"):
        dispute = get_object_or_404(Dispute, pk=data.get("dispute_id"))
        dispute.response = data.get("response", "")
        dispute.status = Dispute.STATUS_RESOLVED
        dispute.resolved_at = timezone.now()
        dispute.save()
        notify(dispute.created_by, "Disputa resuelta", dispute.response)
        return ok({"dispute": {"id": dispute.id, "status": dispute.status}})
    dispute = Dispute.objects.create(
        created_by=profile,
        reservation_id=data.get("reservation_id") or None,
        subject=data.get("subject", "Disputa"),
        description=data.get("description", ""),
    )
    return ok({"dispute": {"id": dispute.id}}, 201)


@csrf_exempt
def dashboard(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if not is_admin(profile):
        return error("Solo administradores.", 403)
    return ok(
        {
            "users": Profile.objects.count(),
            "pending_profiles": Profile.objects.filter(status=Profile.STATUS_PENDING).count(),
            "reservations": Reservation.objects.count(),
            "completed": Reservation.objects.filter(status=Reservation.STATUS_FINISHED).count(),
            "offers": Offer.objects.count(),
            "revenue": money(Payment.objects.filter(status=Payment.STATUS_PAID).aggregate(total=Sum("amount"))["total"]),
            "by_role": list(Profile.objects.values("role").annotate(total=Count("id"))),
            "by_status": list(Reservation.objects.values("status").annotate(total=Count("id"))),
        }
    )


@csrf_exempt
def reports_csv(request):
    profile, denied = require_profile(request)
    if denied:
        return denied
    if not is_admin(profile):
        return error("Solo administradores.", 403)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="lcd-reporte.csv"'
    writer = csv.writer(response)
    writer.writerow(["Metrica", "Valor"])
    writer.writerow(["Usuarios", Profile.objects.count()])
    writer.writerow(["Reservas", Reservation.objects.count()])
    writer.writerow(["Ofertas", Offer.objects.count()])
    writer.writerow(["Ingresos", Payment.objects.filter(status=Payment.STATUS_PAID).aggregate(total=Sum("amount"))["total"] or 0])
    return response
