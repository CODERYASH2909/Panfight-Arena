"""
Management command: python manage.py supabase_init

Performs first-time Supabase integration setup:
  1. Creates the Supabase Storage bucket for avatars
  2. Prints Supabase database connection instructions

Run this ONCE after configuring SUPABASE_URL and SUPABASE_KEY in your .env.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Initialize Supabase Storage bucket and print setup instructions."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n🗄  PenFight Arena — Supabase Init\n"))

        # ── Storage bucket ─────────────────────────────────────────────────────
        try:
            from penfight.supabase_setup import ensure_bucket_exists
            ensure_bucket_exists()
        except Exception as exc:
            self.stderr.write(f"  ❌ Storage bucket error: {exc}")

        # ── Print instructions ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋  SUPABASE DATABASE SETUP INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Create a Supabase project at https://supabase.com/dashboard

2. Go to: Project → Settings → Database → Connection string
   Copy the "Transaction" pooler URI (port 6543):
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

3. Add it to Railway environment variables:
   DATABASE_URL = <paste connection string here>
   USE_REDIS_CHANNEL_LAYER = True
   REDIS_URL = <your Railway Redis URL>
   DEBUG = False
   SECRET_KEY = <generate a 50-char random string>
   ALLOWED_HOSTS = <your-app>.up.railway.app
   CSRF_TRUSTED_ORIGINS = https://<your-app>.up.railway.app

4. Railway will auto-run migrations via railway_startup.sh on every deploy.

5. (Optional) For avatar storage via Supabase:
   SUPABASE_URL = https://<your-ref>.supabase.co
   SUPABASE_KEY = <your service_role or anon key>
   SUPABASE_BUCKET = penfight-avatars
   Then run: python manage.py supabase_init

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""))
