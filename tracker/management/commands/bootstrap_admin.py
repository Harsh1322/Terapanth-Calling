import os
from django.core.management.base import BaseCommand, CommandError
from tracker.models import User
class Command(BaseCommand):
    help = "Create the initial admin account from environment variables."
    def handle(self, *args, **options):
        mobile = os.getenv("ADMIN_MOBILE", "7338884040")
        password = os.getenv("ADMIN_INITIAL_PASSWORD")
        if not password:
            raise CommandError("Set ADMIN_INITIAL_PASSWORD in the Render environment before deployment.")
        user, created = User.objects.get_or_create(mobile=mobile, defaults={"username":"Admin","is_staff":True,"is_superuser":True})
        user.username = "Admin"
        user.is_staff = user.is_superuser = user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(("Created" if created else "Updated") + f" admin account {mobile}"))
