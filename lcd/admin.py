from django.contrib import admin

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


admin.site.register(Profile)
admin.site.register(ProviderService)
admin.site.register(PaymentMethod)
admin.site.register(Reservation)
admin.site.register(Offer)
admin.site.register(OfferApplication)
admin.site.register(Payment)
admin.site.register(Rating)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(Notification)
admin.site.register(Sanction)
admin.site.register(Dispute)
