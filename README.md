# PolKhol

PolKhol is an anonymous group chat app built with FastAPI, server-rendered Jinja templates, Tailwind-ready frontend assets, and vanilla JavaScript WebSockets.

## What it does

- Email + password signup and login
- Private email identity: regular users never see other users' emails
- Non-unique usernames with manual rename and random reset
- Group creation with creator-managed member adds
- Alias-only group rooms where messages and rosters never expose usernames or emails
- Admin account directory tied to `ADMIN_EMAIL`

## Project layout

- `app/main.py`: app factory and router wiring
- `app/routers/`: page, auth, account, and group/WebSocket routes
- `app/services/`: group and identity logic
- `app/templates/`: dark animated UI templates
- `app/static/`: CSS and frontend JavaScript
- `tests/`: integration tests for auth, anonymity, groups, and WebSockets

## Run it locally

1. Create a virtual environment and install Python dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set your owner email and optional secrets.

```powershell
$env:ADMIN_EMAIL = 'you@example.com'
$env:SECRET_KEY = 'replace-me'
```

3. Start the FastAPI app.

```powershell
uvicorn app.main:app --reload
```

4. Open `http://127.0.0.1:8000`.

## Tailwind assets

A ready-to-use stylesheet is checked in at `app/static/css/app.css`.
If you want to rebuild it from the Tailwind source later, use `cmd /c npm ...` on this machine because PowerShell blocks `npm.ps1`.

```powershell
cmd /c npm install
cmd /c npm run build:css
```

## Test status

```powershell
pytest -q
```

The current suite covers signup/login/logout, duplicate-email rejection, admin bootstrap, duplicate usernames, username reset, group add flows, room privacy, and WebSocket message persistence.