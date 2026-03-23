"""
Management command to seed initial data:
- Field sites (Loay Farm, Balilihan Farm)
- Super Admin user
- Sample supervisor and admin users

Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import FieldSite, UserProfile


class Command(BaseCommand):
    help = 'Seed initial data: field sites and sample users'

    def handle(self, *args, **options):
        # Create field sites
        loay, _ = FieldSite.objects.get_or_create(
            name='Loay Farm',
            defaults={'description': 'PCA field site in Loay, Bohol'}
        )
        balilihan, _ = FieldSite.objects.get_or_create(
            name='Balilihan Farm',
            defaults={'description': 'PCA field site in Balilihan, Bohol'}
        )
        self.stdout.write(self.style.SUCCESS('✓ Field sites created'))

        # Create Super Admin (PCDM / Division Chief I)
        if not User.objects.filter(username='superadmin').exists():
            sa = User.objects.create_superuser(
                username='superadmin',
                password='bohol@pca.gov.ph',
                first_name='Super',
                last_name='Admin',
                email='superadmin@pca.gov.ph',
            )
            UserProfile.objects.get_or_create(user=sa, defaults={'role': 'superadmin'})
            self.stdout.write(self.style.SUCCESS('✓ Super Admin / Division Chief created (superadmin / bohol@pca.gov.ph)'))

        # Create Admin (Senior Agriculturist)
        if not User.objects.filter(username='admin1').exists():
            admin_user = User.objects.create_user(
                username='admin1',
                password='bohol@pca.gov.ph',
                first_name='Admin',
                last_name='User',
                email='admin@pca.gov.ph',
            )
            UserProfile.objects.get_or_create(user=admin_user, defaults={'role': 'admin'})
            self.stdout.write(self.style.SUCCESS('✓ Senior Agriculturist created (admin1 / bohol@pca.gov.ph)'))

        # Create Supervisors (COS / Agriculturist)
        if not User.objects.filter(username='loay_supervisor').exists():
            s1 = User.objects.create_user(
                username='loay_supervisor',
                password='bohol@pca.gov.ph',
                first_name='Loay',
                last_name='Supervisor',
            )
            UserProfile.objects.get_or_create(user=s1, defaults={'role': 'supervisor', 'field_site': loay})
            self.stdout.write(self.style.SUCCESS('✓ Loay Agriculturist created (loay_supervisor / bohol@pca.gov.ph)'))

        if not User.objects.filter(username='balilihan_supervisor').exists():
            s2 = User.objects.create_user(
                username='balilihan_supervisor',
                password='bohol@pca.gov.ph',
                first_name='Balilihan',
                last_name='Supervisor',
            )
            UserProfile.objects.get_or_create(user=s2, defaults={'role': 'supervisor', 'field_site': balilihan})
            self.stdout.write(self.style.SUCCESS('✓ Balilihan Agriculturist created (balilihan_supervisor / bohol@pca.gov.ph)'))

        self.stdout.write(self.style.SUCCESS('\n✅ Seed data complete!'))
