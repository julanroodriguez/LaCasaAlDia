from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("api/session/", views.session_view),
    path("api/register/", views.register),
    path("api/login/", views.login_view),
    path("api/logout/", views.logout_view),
    path("api/bootstrap/", views.bootstrap),
    path("api/profile/", views.profile_view),
    path("api/providers/", views.providers),
    path("api/reservations/", views.reservations),
    path("api/reservations/<int:reservation_id>/status/", views.reservation_status),
    path("api/offers/", views.offers),
    path("api/offers/<int:offer_id>/apply/", views.apply_offer),
    path("api/offers/<int:offer_id>/choose/<int:application_id>/", views.choose_application),
    path("api/offers/<int:offer_id>/moderate/", views.moderate_offer),
    path("api/payments/", views.payments),
    path("api/ratings/", views.ratings),
    path("api/messages/", views.messages_view),
    path("api/notifications/", views.notifications),
    path("api/admin/pending-profiles/", views.pending_profiles),
    path("api/admin/profiles/<int:profile_id>/review/", views.review_profile),
    path("api/admin/users/<int:user_id>/sanction/", views.sanction_user),
    path("api/admin/disputes/", views.disputes),
    path("api/admin/reports.csv", views.reports_csv),
    path("api/dashboard/", views.dashboard),
]
