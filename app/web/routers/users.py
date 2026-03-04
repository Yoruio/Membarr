from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.web.deps import get_db, db_read_all_users, db_delete_user, flash, pop_flash

router = APIRouter(prefix='/users')


@router.get('', response_class=HTMLResponse)
async def users_list(request: Request):
    templates = request.app.state.templates
    conn = get_db()
    users = db_read_all_users(conn)
    conn.close()
    return templates.TemplateResponse('users.html', {
        'request': request,
        'flash': pop_flash(request),
        'users': users,
    })


@router.post('/{discord_id}/delete')
async def user_delete(request: Request, discord_id: str):
    conn = get_db()
    db_delete_user(conn, discord_id)
    conn.close()
    flash(request, f'User <code>{discord_id}</code> removed from the database.')
    return RedirectResponse('/users', status_code=302)
