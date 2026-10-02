"""
supabase_setup.py — PenFight Arena Supabase Integration Helpers

This module provides utilities for interacting with Supabase directly from
Django (file uploads, signed URL generation, bucket management).

Usage:
    from penfight.supabase_setup import get_supabase_client, upload_avatar

Environment variables required (set in Railway dashboard):
    SUPABASE_URL   — e.g. https://xyzxyz.supabase.co
    SUPABASE_KEY   — service_role key (keep secret!) or anon key for public ops
    SUPABASE_BUCKET — bucket name (default: penfight-avatars)
"""

import os
import uuid
from pathlib import Path

from django.conf import settings


def get_supabase_client():
    """Returns an authenticated Supabase client, or None if not configured."""
    url = getattr(settings, "SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")
    key = getattr(settings, "SUPABASE_KEY", "") or os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        return None

    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        raise RuntimeError(
            "supabase package is not installed. "
            "Run: pip install supabase"
        )


def upload_avatar(file_obj, username: str, content_type: str = "image/jpeg") -> str | None:
    """
    Uploads a user avatar to Supabase Storage.

    Args:
        file_obj:     File-like object (e.g. InMemoryUploadedFile from Django form)
        username:     Used to generate a deterministic file path
        content_type: MIME type of the image

    Returns:
        Public URL of the uploaded file, or None if Supabase is not configured.

    Falls back gracefully — if Supabase is not configured the caller should
    save the file to MEDIA_ROOT instead.
    """
    client = get_supabase_client()
    if client is None:
        return None

    bucket = settings.SUPABASE_BUCKET
    ext = Path(file_obj.name).suffix or ".jpg"
    # e.g. avatars/alice_3f7a.jpg  — unique-ish but deterministic per session
    file_path = f"avatars/{username}_{uuid.uuid4().hex[:8]}{ext}"

    data = file_obj.read()
    client.storage.from_(bucket).upload(
        path=file_path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    # Return a public URL (bucket must have public policy, or use signed URL below)
    public_url = client.storage.from_(bucket).get_public_url(file_path)
    return public_url


def get_signed_avatar_url(file_path: str, expires_in: int = 3600) -> str | None:
    """
    Generates a signed (temporary) URL for a private Supabase Storage file.

    Args:
        file_path:  Path inside the bucket (e.g. 'avatars/alice_3f7a.jpg')
        expires_in: URL validity in seconds (default 1 hour)

    Returns:
        Signed URL string, or None if Supabase is not configured.
    """
    client = get_supabase_client()
    if client is None:
        return None

    bucket = settings.SUPABASE_BUCKET
    result = client.storage.from_(bucket).create_signed_url(file_path, expires_in)
    return result.get("signedURL")


def ensure_bucket_exists():
    """
    Creates the Supabase Storage bucket if it doesn't exist.
    Call this during first-time setup / migrations.
    Requires a service_role key with storage management permissions.
    """
    client = get_supabase_client()
    if client is None:
        print("Supabase not configured — skipping bucket creation.")
        return

    bucket = settings.SUPABASE_BUCKET
    existing = [b.name for b in client.storage.list_buckets()]
    if bucket not in existing:
        client.storage.create_bucket(bucket, options={"public": True})
        print(f"✅ Created Supabase Storage bucket: {bucket}")
    else:
        print(f"ℹ  Supabase Storage bucket already exists: {bucket}")
