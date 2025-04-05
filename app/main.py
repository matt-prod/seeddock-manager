from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logo_path = "/srv/sdm/includes/logo.sh"
    logo_content = ""

    if os.path.exists(logo_path):
        with open(logo_path, "r") as f:
            logo_content = f.read()

    return templates.TemplateResponse("index.html", {"request": request, "logo": logo_content})
