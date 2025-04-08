from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os
import yaml
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

vault_path = "/srv/sdm/SeedDock/SDM/group_vars/all.yml"
vault_pass_file = "/srv/sdm/SeedDock/SDM/vault_pass"
logo_script = "/srv/sdm/includes/logo.sh"
variables_script = "/srv/sdm/includes/variables.sh"

def get_logo_output():
    if not os.path.exists(logo_script):
        return "[ERREUR] Fichier logo.sh introuvable"
    try:
        result = subprocess.run(
            ["bash", "-c", f"source {variables_script} && source {logo_script} && show_logo"],
            capture_output=True, text=True, timeout=2
        )
        return Ansi2HTMLConverter().convert(result.stdout, full=False) if result.returncode == 0 else "[ERREUR] Impossible d'afficher le logo"
    except Exception as e:
        return f"[Exception] {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logo = get_logo_output()
    return templates.TemplateResponse("index.html", {"request": request, "logo": logo})

@app.get("/step1", response_class=HTMLResponse)
async def step1(request: Request):
    logo = get_logo_output()
    return templates.TemplateResponse("step1.html", {"request": request, "logo": logo})

@app.post("/step1")
async def step1_post(username: str = Form(...), password: str = Form(...)):
    result = subprocess.run(["ansible-vault", "view", "--vault-password-file", vault_pass_file, vault_path], capture_output=True, text=True)
    data = yaml.safe_load(result.stdout) if result.returncode == 0 else {}
    data["user"] = {"name": username, "password": password}
    with open("/tmp/tmp.yml", "w") as tmp:
        yaml.dump(data, tmp)
    subprocess.run(["ansible-vault", "encrypt", "--vault-password-file", vault_pass_file, "--output", vault_path, "/tmp/tmp.yml"])
    os.remove("/tmp/tmp.yml")
    return RedirectResponse("/step2", status_code=303)

@app.get("/step2", response_class=HTMLResponse)
async def step2(request: Request):
    return HTMLResponse("🚧 Étape 2 à implémenter 🚧")
