from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import subprocess
import ansible.constants as C
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.cli import CLI
from ansible.utils.display import Display
from ansi2html import Ansi2HTMLConverter
import yaml

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")


def get_logo_output():
    logo_script = "/srv/sdm/includes/logo.sh"
    variables_script = "/srv/sdm/includes/variables.sh"

    if not os.path.exists(logo_script):
        return "[ERREUR] Fichier logo.sh introuvable"

    try:
        result = subprocess.run(
            ["bash", "-c", f"source {variables_script} && source {logo_script} && print_logo"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            conv = Ansi2HTMLConverter()
            return conv.convert(result.stdout, full=False)
        else:
            return "[ERREUR] Impossible d'afficher le logo"
    except Exception as e:
        return f"[Exception] {str(e)}"


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logo_content = get_logo_output()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "logo": logo_content,
    })


@app.get("/step1", response_class=HTMLResponse)
async def show_step1(request: Request):
    return templates.TemplateResponse("step1.html", {"request": request})


@app.post("/step1", response_class=HTMLResponse)
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    vault_path = "/srv/sdm/SeedDock/SDM/group_vars/all.yml"
    vault_pass_file = "/srv/sdm/SeedDock/SDM/vault_pass"

    if not os.path.exists(vault_pass_file):
        return HTMLResponse(content="Erreur : vault_pass introuvable.", status_code=500)

    try:
        # Lecture du fichier vault déchiffré
        result = subprocess.run(
            ["ansible-vault", "view", "--vault-password-file", vault_pass_file, vault_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return HTMLResponse(content="Erreur : impossible de lire le fichier vault.", status_code=500)

        data = yaml.safe_load(result.stdout) or {}
        data["user"] = {"name": username, "password": password}

        # Réécriture du fichier vault avec les données mises à jour
        with open("/tmp/all_tmp.yml", "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        subprocess.run(
            ["ansible-vault", "encrypt", "--vault-password-file", vault_pass_file, "--output", vault_path, "/tmp/all_tmp.yml"],
            check=True
        )
        os.remove("/tmp/all_tmp.yml")

        return RedirectResponse("/", status_code=302)

    except Exception as e:
        return HTMLResponse(content=f"Erreur : {e}", status_code=500)
