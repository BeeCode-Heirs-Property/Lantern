from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
import random
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def get_current_user(request: Request):
    return request.session.get("user")


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username and password:
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales incorrectas"})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: str = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/cases", response_class=HTMLResponse)
async def list_cases(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://beecode-api.azurewebsites.net/api/records")

    if response.status_code == 200 and response.text:
        cases = response.json()
    else:
        cases = []

    estados = [
        "Completed first form"
    ]

    for case in cases:
        case["status"] = random.choice(estados)
        case["created_at"] = (datetime.today() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")

    return templates.TemplateResponse("cases.html", {
        "request": request,
        "cases": cases
    })


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
