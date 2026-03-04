from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.web.deps import (
    read_config, write_config, delete_server_config, get_server_config,
    list_server_names, save_server_config, flash, pop_flash,
)

router = APIRouter(prefix='/servers')
BOT_SECTION = 'bot_envs'

RESTART_MSG = 'Settings saved. <strong>Restart the bot</strong> for changes to take effect.'


def _t(request: Request):
    return request.app.state.templates


# ── Server list ───────────────────────────────────────────────────────────────

@router.get('', response_class=HTMLResponse)
async def servers_list(request: Request):
    cfg = read_config()
    jf_names = list_server_names(cfg, 'jellyfin')
    emby_names = list_server_names(cfg, 'emby')

    return _t(request).TemplateResponse('servers.html', {
        'request': request,
        'flash': pop_flash(request),
        'jf_servers': [get_server_config(cfg, 'jellyfin', n) for n in jf_names],
        'emby_servers': [get_server_config(cfg, 'emby', n) for n in emby_names],
        'plex': {
            'base_url': cfg.get(BOT_SECTION, 'plex_base_url', fallback=''),
            'token': cfg.get(BOT_SECTION, 'plex_token', fallback=''),
            'server_name': cfg.get(BOT_SECTION, 'plex_server_name', fallback=''),
            'user': cfg.get(BOT_SECTION, 'plex_user', fallback=''),
            'roles': cfg.get(BOT_SECTION, 'plex_roles', fallback=''),
            'libs': cfg.get(BOT_SECTION, 'plex_libs', fallback='all'),
            'enabled': cfg.get(BOT_SECTION, 'plex_enabled', fallback='false').lower() == 'true',
        },
        'jellyseerr': {
            'url': cfg.get(BOT_SECTION, 'jellyseerr_url', fallback=''),
            'api_key': cfg.get(BOT_SECTION, 'jellyseerr_api_key', fallback=''),
            'jellyfin_server': cfg.get(BOT_SECTION, 'jellyseerr_jellyfin_server', fallback=''),
        },
    })


# ── Jellyfin servers ──────────────────────────────────────────────────────────

@router.get('/jellyfin/new', response_class=HTMLResponse)
async def jellyfin_new(request: Request):
    return _t(request).TemplateResponse('server_edit.html', {
        'request': request,
        'flash': pop_flash(request),
        'server_type': 'jellyfin',
        'server_type_label': 'Jellyfin',
        'is_new': True,
        'server': {'name': '', 'url': '', 'api_key': '', 'external_url': '',
                   'roles': '', 'libs': 'all', 'enabled': True},
    })


@router.post('/jellyfin/new')
async def jellyfin_new_post(
    request: Request,
    server_name: str = Form(...),
    url: str = Form(''),
    api_key: str = Form(''),
    external_url: str = Form(''),
    roles: str = Form(''),
    libs: str = Form('all'),
    enabled: str = Form(''),
):
    server_name = server_name.strip()
    if not server_name:
        flash(request, 'Server name is required.', 'danger')
        return RedirectResponse('/servers/jellyfin/new', status_code=302)
    save_server_config('jellyfin', server_name, {
        'url': url.rstrip('/'),
        'api_key': api_key,
        'external_url': external_url.rstrip('/'),
        'roles': roles,
        'libs': libs or 'all',
        'enabled': 'true' if enabled else 'false',
    })
    flash(request, RESTART_MSG)
    return RedirectResponse('/servers', status_code=302)


@router.get('/jellyfin/{name}', response_class=HTMLResponse)
async def jellyfin_edit(request: Request, name: str):
    cfg = read_config()
    return _t(request).TemplateResponse('server_edit.html', {
        'request': request,
        'flash': pop_flash(request),
        'server_type': 'jellyfin',
        'server_type_label': 'Jellyfin',
        'is_new': False,
        'server': get_server_config(cfg, 'jellyfin', name),
    })


@router.post('/jellyfin/{name}')
async def jellyfin_edit_post(
    request: Request,
    name: str,
    url: str = Form(''),
    api_key: str = Form(''),
    external_url: str = Form(''),
    roles: str = Form(''),
    libs: str = Form('all'),
    enabled: str = Form(''),
):
    save_server_config('jellyfin', name, {
        'url': url.rstrip('/'),
        'api_key': api_key,
        'external_url': external_url.rstrip('/'),
        'roles': roles,
        'libs': libs or 'all',
        'enabled': 'true' if enabled else 'false',
    })
    flash(request, RESTART_MSG)
    return RedirectResponse('/servers', status_code=302)


@router.post('/jellyfin/{name}/delete')
async def jellyfin_delete(request: Request, name: str):
    delete_server_config('jellyfin', name)
    flash(request, f'Jellyfin server <strong>{name}</strong> removed. {RESTART_MSG}')
    return RedirectResponse('/servers', status_code=302)


# ── Emby servers ──────────────────────────────────────────────────────────────

@router.get('/emby/new', response_class=HTMLResponse)
async def emby_new(request: Request):
    return _t(request).TemplateResponse('server_edit.html', {
        'request': request,
        'flash': pop_flash(request),
        'server_type': 'emby',
        'server_type_label': 'Emby',
        'is_new': True,
        'server': {'name': '', 'url': '', 'api_key': '', 'external_url': '',
                   'roles': '', 'libs': 'all', 'enabled': True},
    })


@router.post('/emby/new')
async def emby_new_post(
    request: Request,
    server_name: str = Form(...),
    url: str = Form(''),
    api_key: str = Form(''),
    external_url: str = Form(''),
    roles: str = Form(''),
    libs: str = Form('all'),
    enabled: str = Form(''),
):
    server_name = server_name.strip()
    if not server_name:
        flash(request, 'Server name is required.', 'danger')
        return RedirectResponse('/servers/emby/new', status_code=302)
    save_server_config('emby', server_name, {
        'url': url.rstrip('/'),
        'api_key': api_key,
        'external_url': external_url.rstrip('/'),
        'roles': roles,
        'libs': libs or 'all',
        'enabled': 'true' if enabled else 'false',
    })
    flash(request, RESTART_MSG)
    return RedirectResponse('/servers', status_code=302)


@router.get('/emby/{name}', response_class=HTMLResponse)
async def emby_edit(request: Request, name: str):
    cfg = read_config()
    return _t(request).TemplateResponse('server_edit.html', {
        'request': request,
        'flash': pop_flash(request),
        'server_type': 'emby',
        'server_type_label': 'Emby',
        'is_new': False,
        'server': get_server_config(cfg, 'emby', name),
    })


@router.post('/emby/{name}')
async def emby_edit_post(
    request: Request,
    name: str,
    url: str = Form(''),
    api_key: str = Form(''),
    external_url: str = Form(''),
    roles: str = Form(''),
    libs: str = Form('all'),
    enabled: str = Form(''),
):
    save_server_config('emby', name, {
        'url': url.rstrip('/'),
        'api_key': api_key,
        'external_url': external_url.rstrip('/'),
        'roles': roles,
        'libs': libs or 'all',
        'enabled': 'true' if enabled else 'false',
    })
    flash(request, RESTART_MSG)
    return RedirectResponse('/servers', status_code=302)


@router.post('/emby/{name}/delete')
async def emby_delete(request: Request, name: str):
    delete_server_config('emby', name)
    flash(request, f'Emby server <strong>{name}</strong> removed. {RESTART_MSG}')
    return RedirectResponse('/servers', status_code=302)


# ── Plex ──────────────────────────────────────────────────────────────────────

@router.post('/plex')
async def plex_save(
    request: Request,
    plex_base_url: str = Form(''),
    plex_token: str = Form(''),
    plex_server_name: str = Form(''),
    plex_user: str = Form(''),
    plex_pass: str = Form(''),
    plex_roles: str = Form(''),
    plex_libs: str = Form('all'),
    plex_enabled: str = Form(''),
):
    fields = {
        'plex_base_url': plex_base_url.rstrip('/'),
        'plex_token': plex_token,
        'plex_server_name': plex_server_name,
        'plex_user': plex_user,
        'plex_pass': plex_pass,
        'plex_roles': plex_roles,
        'plex_libs': plex_libs or 'all',
        'plex_enabled': 'true' if plex_enabled else 'false',
    }
    for key, value in fields.items():
        write_config(key, value)
    flash(request, RESTART_MSG)
    return RedirectResponse('/servers', status_code=302)


# ── Jellyseerr ────────────────────────────────────────────────────────────────

@router.post('/jellyseerr')
async def jellyseerr_save(
    request: Request,
    jellyseerr_url: str = Form(''),
    jellyseerr_api_key: str = Form(''),
    jellyseerr_jellyfin_server: str = Form(''),
):
    write_config('jellyseerr_url', jellyseerr_url.rstrip('/'))
    write_config('jellyseerr_api_key', jellyseerr_api_key)
    write_config('jellyseerr_jellyfin_server', jellyseerr_jellyfin_server)
    flash(request, RESTART_MSG)
    return RedirectResponse('/servers', status_code=302)
