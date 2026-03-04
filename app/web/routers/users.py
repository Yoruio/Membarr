from typing import List, Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.web.deps import (
    get_db, db_read_all_users, db_delete_user,
    db_get_user, db_update_user, db_replace_server_accounts,
    read_config, list_server_names,
    flash, pop_flash,
)

router = APIRouter(prefix='/users')


@router.get('', response_class=HTMLResponse)
async def users_list(request: Request):
    templates = request.app.state.templates
    conn = get_db()
    users = db_read_all_users(conn)
    conn.close()
    cfg = read_config()
    return templates.TemplateResponse('users.html', {
        'request': request,
        'flash': pop_flash(request),
        'users': users,
        'jellyfin_names': list_server_names(cfg, 'jellyfin'),
        'emby_names': list_server_names(cfg, 'emby'),
    })


@router.post('/{discord_id}/delete')
async def user_delete(request: Request, discord_id: str):
    conn = get_db()
    db_delete_user(conn, discord_id)
    conn.close()
    flash(request, f'User <code>{discord_id}</code> removed from the database.')
    return RedirectResponse('/users', status_code=302)


@router.get('/{discord_id}/edit', response_class=HTMLResponse)
async def user_edit_get(request: Request, discord_id: str):
    templates = request.app.state.templates
    conn = get_db()
    user = db_get_user(conn, discord_id)
    conn.close()
    if user is None:
        flash(request, f'User <code>{discord_id}</code> not found.', 'danger')
        return RedirectResponse('/users', status_code=302)
    cfg = read_config()
    return templates.TemplateResponse('user_edit.html', {
        'request': request,
        'flash': pop_flash(request),
        'user': user,
        'jellyfin_names': list_server_names(cfg, 'jellyfin'),
        'emby_names': list_server_names(cfg, 'emby'),
    })


@router.post('/{discord_id}/edit')
async def user_edit_post(
    request: Request,
    discord_id: str,
    new_discord_id: str = Form(...),
    email: str = Form(''),
    account_type: List[str] = Form(default=[]),
    account_name: List[str] = Form(default=[]),
    account_username: List[str] = Form(default=[]),
):
    accounts = [
        {'server_type': t, 'server_name': n, 'username': u}
        for t, n, u in zip(account_type, account_name, account_username)
        if u.strip()
    ]
    conn = get_db()
    db_update_user(conn, discord_id, new_discord_id.strip(), email.strip())
    db_replace_server_accounts(conn, new_discord_id.strip(), accounts)
    conn.close()
    flash(request, f'User <code>{new_discord_id}</code> updated.')
    return RedirectResponse('/users', status_code=302)
