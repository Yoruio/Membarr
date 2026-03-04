import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.web.routers import auth, dashboard, servers, users, requests as reqs

# Load same bot.env as the Discord bot so WEB_PASSWORD / WEB_SECRET_KEY work
if os.path.exists('bot.env'):
    load_dotenv('bot.env')

WEB_PASSWORD = os.environ.get('WEB_PASSWORD', '')
WEB_SECRET_KEY = os.environ.get('WEB_SECRET_KEY', secrets.token_hex(32))

app = FastAPI(title='Membarr Admin', docs_url=None, redoc_url=None)

# ── Jinja2 globals available in every template ────────────────────────────────
templates = Jinja2Templates(directory='app/web/templates')
templates.env.globals['web_password'] = WEB_PASSWORD


@app.middleware('http')
async def auth_middleware(request: Request, call_next):
    """Redirect unauthenticated requests to /login when a password is configured."""
    public = {'/login', '/logout'}
    if WEB_PASSWORD and request.url.path not in public:
        if not request.session.get('authenticated'):
            return RedirectResponse(url='/login', status_code=302)
    return await call_next(request)


# SessionMiddleware must be added AFTER the auth middleware decorator so it
# becomes the outermost layer and populates request.session before auth runs.
app.add_middleware(
    SessionMiddleware,
    secret_key=WEB_SECRET_KEY,
    session_cookie='membarr_session',
    max_age=86400,
)


# Share templates + password with routers via app.state
app.state.templates = templates
app.state.web_password = WEB_PASSWORD

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(servers.router)
app.include_router(users.router)
app.include_router(reqs.router)
