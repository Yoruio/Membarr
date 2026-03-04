from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.web.deps import (
    read_config, get_db, db_get_stats, list_server_names, get_server_config, pop_flash
)
import app.bot.helper.jellyseerrhelper as jellyseerr

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
async def dashboard(request: Request):
    templates = request.app.state.templates
    cfg = read_config()
    conn = get_db()

    stats = db_get_stats(conn)
    conn.close()

    # Build server summaries
    jf_names = list_server_names(cfg, 'jellyfin')
    emby_names = list_server_names(cfg, 'emby')
    jf_servers = [get_server_config(cfg, 'jellyfin', n) for n in jf_names]
    emby_servers = [get_server_config(cfg, 'emby', n) for n in emby_names]

    # Plex status
    try:
        plex_enabled = cfg.get('bot_envs', 'plex_enabled', fallback='false').lower() == 'true'
    except Exception:
        plex_enabled = False

    # Jellyseerr
    js_url = cfg.get('bot_envs', 'jellyseerr_url', fallback='')
    js_key = cfg.get('bot_envs', 'jellyseerr_api_key', fallback='')
    pending_count = 0
    js_configured = bool(js_url and js_key)
    if js_configured:
        try:
            pending = jellyseerr.get_all_requests(js_url, js_key, 'pending', take=50)
            pending_count = len(pending)
        except Exception:
            pass

    return templates.TemplateResponse('dashboard.html', {
        'request': request,
        'flash': pop_flash(request),
        'stats': stats,
        'jf_servers': jf_servers,
        'emby_servers': emby_servers,
        'plex_enabled': plex_enabled,
        'js_configured': js_configured,
        'pending_count': pending_count,
    })
