from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.web.deps import (
    read_config, write_config,
    read_bot_env, write_bot_env_key,
    flash, pop_flash,
    BOT_SECTION,
)

router = APIRouter(prefix='/settings')


@router.get('', response_class=HTMLResponse)
async def settings_get(request: Request):
    templates = request.app.state.templates
    env = read_bot_env()
    token = env.get('discord_bot_token', '')
    cfg = read_config()
    allowed_channels = cfg.get(BOT_SECTION, 'allowed_channels', fallback='')
    return templates.TemplateResponse('settings.html', {
        'request': request,
        'flash': pop_flash(request),
        'token': token,
        'allowed_channels': allowed_channels,
    })


@router.post('', response_class=HTMLResponse)
async def settings_post(
    request: Request,
    token: str = Form(''),
    allowed_channels: str = Form(''),
):
    if token:
        write_bot_env_key('discord_bot_token', token)
    # Normalise channel list: strip spaces around commas
    channels_clean = ','.join(c.strip() for c in allowed_channels.split(',') if c.strip())
    write_config('allowed_channels', channels_clean)
    flash(request, 'Settings saved. Restart the bot for token changes to take effect.', 'success')
    return RedirectResponse('/settings', status_code=302)
