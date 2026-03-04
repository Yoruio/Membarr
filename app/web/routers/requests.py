from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import app.bot.helper.jellyseerrhelper as jellyseerr
from app.web.deps import read_config, flash, pop_flash

router = APIRouter(prefix='/requests')


def _js_creds(cfg):
    url = cfg.get('bot_envs', 'jellyseerr_url', fallback='').rstrip('/')
    key = cfg.get('bot_envs', 'jellyseerr_api_key', fallback='')
    return url, key


@router.get('', response_class=HTMLResponse)
async def requests_list(request: Request):
    templates = request.app.state.templates
    cfg = read_config()
    url, key = _js_creds(cfg)

    if not (url and key):
        return templates.TemplateResponse('requests.html', {
            'request': request,
            'flash': pop_flash(request),
            'configured': False,
            'requests': [],
        })

    filter_status = request.query_params.get('filter', 'pending')
    try:
        reqs = jellyseerr.get_all_requests(url, key, filter_status, take=40)
    except Exception as e:
        reqs = []
        flash(request, f'Could not reach Jellyseerr: {e}', 'danger')

    return templates.TemplateResponse('requests.html', {
        'request': request,
        'flash': pop_flash(request),
        'configured': True,
        'requests': reqs,
        'filter_status': filter_status,
        'format_status': jellyseerr.format_status,
        'format_media_type': jellyseerr.format_media_type,
    })


@router.post('/{request_id}/approve')
async def approve(request: Request, request_id: int):
    cfg = read_config()
    url, key = _js_creds(cfg)
    ok = jellyseerr.approve_request(url, key, request_id)
    if ok:
        flash(request, f'Request #{request_id} approved.')
    else:
        flash(request, f'Failed to approve request #{request_id}.', 'danger')
    return RedirectResponse('/requests', status_code=302)


@router.post('/{request_id}/decline')
async def decline(request: Request, request_id: int):
    cfg = read_config()
    url, key = _js_creds(cfg)
    ok = jellyseerr.decline_request(url, key, request_id)
    if ok:
        flash(request, f'Request #{request_id} declined.')
    else:
        flash(request, f'Failed to decline request #{request_id}.', 'danger')
    return RedirectResponse('/requests', status_code=302)
