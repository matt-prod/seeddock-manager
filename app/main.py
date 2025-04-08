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
async def show_step1(request: Request):
    return templates.TemplateResponse("step1.html", {"request": request})


@app.post("/step1")
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    vault_path = "/srv/sdm/SeedDock/SDM/group_vars/all.yml"
    vault_pass_file = "/srv/sdm/SeedDock/SDM/vault_pass"

    # Vérifier que le fichier vault_pass existe
    if not os.path.exists(vault_pass_file):
        return HTMLResponse("Erreur : fichier vault_pass manquant.", status_code=500)

    try:
        # Lecture du vault existant
        result = subprocess.run(
            ["ansible-vault", "view", vault_path, "--vault-password-file", vault_pass_file],
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}

        # Mise à jour des infos admin
        data["user"] = {"name": username, "password": password}

        # Sauvegarde temporaire en clair
        tmp_vault = "/tmp/all.yml"
        with open(tmp_vault, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        # Chiffrement
        subprocess.run(
            ["ansible-vault", "encrypt", tmp_vault, "--vault-password-file", vault_pass_file, "--output", vault_path],
            check=True
        )

        # Suppression du fichier temporaire
        os.remove(tmp_vault)

        # On redirige vers la page de succès ou suivante
        return RedirectResponse("/step1_success", status_code=302)

    except subprocess.CalledProcessError as e:
        return HTMLResponse(f"Erreur Ansible Vault : {e.stderr}", status_code=500)
    except Exception as e:
        return HTMLResponse(f"Erreur interne : {str(e)}", status_code=500)


@app.get("/step1_success", response_class=HTMLResponse)
async def step1_success(request: Request):
    return HTMLResponse("""
    <html><body style='text-align: center; font-family: Arial;'>
    <h2>✅ Compte admin cree avec succes !</h2>
    <a href="/step2">Suivant</a>
    </body></html>
    """)

@app.get("/step2", response_class=HTMLResponse)
async def step2(request: Request):
    return HTMLResponse("Etape 2 a implementer")
