import os
from django.core.management.base import BaseCommand
from tracker.models import User
class Command(BaseCommand):
    help = "Create the initial admin account from environment variables."
    def handle(self, *args, **options):
        mobile = os.getenv("ADMIN_MOBILE", "7338884040")
        password = os.getenv("ADMIN_INITIAL_PASSWORD")
        user, created = User.objects.get_or_create(mobile=mobile, defaults={"username":"Admin","is_staff":True,"is_superuser":True})
        user.username = "Admin"
        user.is_staff = user.is_superuser = user.is_active = True
        if password:
            user.set_password(password)
        elif created:
            user.set_unusable_password()
        user.save()
        self.stdout.write(self.style.SUCCESS(("Created" if created else "Updated") + f" admin account {mobile}"))
