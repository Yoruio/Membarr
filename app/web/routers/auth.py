import secrets

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


def _templates(request: Request):
    return request.app.state.templates


@router.get('/login', response_class=HTMLResponse)
async def login_get(request: Request):
    if not request.app.state.web_password:
        return RedirectResponse('/', status_code=302)
    if request.session.get('authenticated'):
        return RedirectResponse('/', status_code=302)
    return _templates(request).TemplateResponse('login.html', {'request': request, 'error': None})


@router.post('/login')
async def login_post(request: Request, password: str = Form(...)):
    web_password = request.app.state.web_password
    if secrets.compare_digest(password, web_password):
        request.session['authenticated'] = True
        return RedirectResponse('/', status_code=302)
    return _templates(request).TemplateResponse(
        'login.html', {'request': request, 'error': 'Incorrect password.'}, status_code=401
    )


@router.post('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=302)
