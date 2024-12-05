from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import num_counters
from .views import initialize_counters

@receiver(post_save, sender=num_counters)
def update_counters(sender, instance, **kwargs):
    initialize_counters()
