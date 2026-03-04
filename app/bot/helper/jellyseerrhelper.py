"""
jellyseerrhelper.py — Jellyseerr/Overseerr REST API wrapper.

Jellyseerr users are matched to Discord users via their Jellyfin username
(stored in the server_accounts table). Jellyseerr imports users from Jellyfin,
and their displayName matches the Jellyfin username.
"""

import requests
from typing import Optional


def _headers(api_key: str) -> dict:
    return {"X-Api-Key": api_key, "Content-Type": "application/json"}


def get_status(url: str, api_key: str) -> int:
    """Return HTTP status code for a connectivity check."""
    r = requests.get(f"{url}/api/v1/status", headers=_headers(api_key), timeout=5)
    return r.status_code


# ── User lookup ───────────────────────────────────────────────────────────────

def get_all_users(url: str, api_key: str) -> list:
    """Return all Jellyseerr users (paginated, up to 500)."""
    users = []
    take = 50
    skip = 0
    while True:
        r = requests.get(
            f"{url}/api/v1/user",
            headers=_headers(api_key),
            params={"take": take, "skip": skip},
            timeout=10,
        )
        if r.status_code != 200:
            break
        data = r.json()
        page_users = data.get("results", [])
        users.extend(page_users)
        if len(users) >= data.get("pageInfo", {}).get("results", 0):
            break
        skip += take
    return users


def find_user_by_jellyfin_username(url: str, api_key: str, jellyfin_username: str) -> Optional[dict]:
    """Find a Jellyseerr user whose displayName matches the given Jellyfin username."""
    users = get_all_users(url, api_key)
    target = jellyfin_username.lower()
    for user in users:
        if user.get("displayName", "").lower() == target:
            return user
        # Also try jellyfinUsername field if present
        if user.get("jellyfinUsername", "").lower() == target:
            return user
    return None


# ── Requests ──────────────────────────────────────────────────────────────────

def get_user_requests(url: str, api_key: str, user_id: int, filter_status: str = "all") -> list:
    """Return requests for a specific Jellyseerr user."""
    params = {"take": 25, "skip": 0}
    if filter_status != "all":
        params["filter"] = filter_status
    r = requests.get(
        f"{url}/api/v1/user/{user_id}/requests",
        headers=_headers(api_key),
        params=params,
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def get_all_requests(url: str, api_key: str, filter_status: str = "pending", take: int = 20) -> list:
    """Return recent requests across all users."""
    params = {"take": take, "skip": 0}
    if filter_status != "all":
        params["filter"] = filter_status
    r = requests.get(
        f"{url}/api/v1/request",
        headers=_headers(api_key),
        params=params,
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def approve_request(url: str, api_key: str, request_id: int) -> bool:
    """Approve a pending request."""
    r = requests.post(
        f"{url}/api/v1/request/{request_id}/approve",
        headers=_headers(api_key),
        timeout=10,
    )
    return r.status_code in (200, 204)


def decline_request(url: str, api_key: str, request_id: int) -> bool:
    """Decline a pending request."""
    r = requests.post(
        f"{url}/api/v1/request/{request_id}/decline",
        headers=_headers(api_key),
        timeout=10,
    )
    return r.status_code in (200, 204)


# ── Search ────────────────────────────────────────────────────────────────────

def search(url: str, api_key: str, query: str, page: int = 1) -> list:
    """Search for movies and TV shows. Returns list of result dicts."""
    r = requests.get(
        f"{url}/api/v1/search",
        headers=_headers(api_key),
        params={"query": query, "page": page, "language": "en"},
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def request_media(url: str, api_key: str, media_type: str, media_id: int,
                  seasons: Optional[list] = None) -> Optional[dict]:
    """Create a new media request.

    media_type: 'movie' or 'tv'
    media_id:   TMDB ID
    seasons:    list of season numbers (for TV, None = all)
    """
    payload = {"mediaType": media_type, "mediaId": media_id}
    if media_type == "tv":
        payload["seasons"] = seasons or "all"
    r = requests.post(
        f"{url}/api/v1/request",
        headers=_headers(api_key),
        json=payload,
        timeout=10,
    )
    if r.status_code in (200, 201):
        return r.json()
    return None


# ── Formatting helpers ────────────────────────────────────────────────────────

def format_status(status_code: int) -> str:
    """Convert Jellyseerr request status int to a human-readable string."""
    return {
        1: "⏳ Pending",
        2: "✅ Approved",
        3: "❌ Declined",
        4: "🔄 Available",
        5: "📥 Processing",
    }.get(status_code, f"Unknown ({status_code})")


def format_media_type(media_type: str) -> str:
    return {"movie": "🎬 Movie", "tv": "📺 TV Show"}.get(media_type, media_type)
