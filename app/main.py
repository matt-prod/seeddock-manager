from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os
import yaml
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

# Chemins centralisés
SDM_BASE_DIR = "/srv/sdm"
vault_path = f"{SDM_BASE_DIR}/SeedDock/SDM/group_vars/all.yml"
vault_pass_file = f"{SDM_BASE_DIR}/SeedDock/SDM/config/vault_pass"
logo_script = f"{SDM_BASE_DIR}/includes/logo.sh"
variables_script = f"{SDM_BASE_DIR}/includes/variables.sh"
ansible_cwd = SDM_BASE_DIR  # Pour le ansible.cfg

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
    if os.path.exists(vault_path) and os.path.exists(vault_pass_file):
        try:
            with open(vault_path, "r") as f:
                if not f.readline().strip().startswith("$ANSIBLE_VAULT"):
                    subprocess.run(
                        ["ansible-vault", "encrypt", vault_path, "--vault-password-file", vault_pass_file],
                        check=True
                    )
        except Exception as e:
            return HTMLResponse(f"Erreur lors du chiffrement initial : {e}", status_code=500)
    return templates.TemplateResponse("step1.html", {"request": request})

@app.post("/step1")
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", "./group_vars/all.yml"],
            cwd=ansible_cwd,
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["user"] = {"name": username, "password": password}
        data["account"] = {"admin": 1}

        tmp_vault = "/tmp/all.yml"
        with open(tmp_vault, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        subprocess.run(
            ["ansible-vault", "encrypt", tmp_vault, "--output", "./group_vars/all.yml"],
            cwd=ansible_cwd,
            check=True
        )

        os.remove(tmp_vault)
        return RedirectResponse("/step1_success", status_code=302)

    except subprocess.CalledProcessError as e:
        return HTMLResponse(f"Erreur Ansible Vault : {e.stderr}", status_code=500)
    except Exception as e:
        return HTMLResponse(f"Erreur interne : {str(e)}", status_code=500)

@app.get("/step1_success", response_class=HTMLResponse)
async def step1_success(request: Request):
    return HTMLResponse("""
    <html><body style='text-align: center; font-family: Arial;'>
    <h2>Compte admin créé avec succès.</h2>
    <a href="/step2">Suivant</a>
    </body></html>
    """)

# Step 2 : IP et IPv6
@app.get("/step2", response_class=HTMLResponse)
async def step2(request: Request):
    return templates.TemplateResponse("step2.html", {"request": request})


@app.post("/step2")
async def handle_step2(request: Request, enable_ipv6: str = Form(...)):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", vault_path, "--vault-password-file", vault_pass_file],
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["network"] = {"ipv6": bool(enable_ipv6)}

        with open("/tmp/all.yml", "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        subprocess.run(
            ["ansible-vault", "encrypt", "/tmp/all.yml", "--vault-password-file", vault_pass_file, "--output", vault_path],
            check=True
        )
        os.remove("/tmp/all.yml")
        return RedirectResponse("/step3", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur étape 2 : {e}", status_code=500)


# Step 3 : Nom de domaine et provider DNS
@app.get("/step3", response_class=HTMLResponse)
async def step3(request: Request):
    return templates.TemplateResponse("step3.html", {"request": request})


@app.post("/step3")
async def handle_step3(
    request: Request,
    domain_enabled: str = Form(...),
    domain_name: str = Form(""),
    provider: str = Form("")
):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", vault_path, "--vault-password-file", vault_pass_file],
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["domain"] = {
            "enabled": domain_enabled == "yes",
            "name": domain_name,
            "provider": provider
        }

        with open("/tmp/all.yml", "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        subprocess.run(
            ["ansible-vault", "encrypt", "/tmp/all.yml", "--vault-password-file", vault_pass_file, "--output", vault_path],
            check=True
        )
        os.remove("/tmp/all.yml")
        return RedirectResponse("/step4", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur étape 3 : {e}", status_code=500)


# Step 4 : Configuration mail et certificat
@app.get("/step4", response_class=HTMLResponse)
async def step4(request: Request):
    return templates.TemplateResponse("step4.html", {"request": request})


@app.post("/step4")
async def handle_step4(request: Request, email: str = Form(...)):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", vault_path, "--vault-password-file", vault_pass_file],
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["certbot"] = {"email": email}

        with open("/tmp/all.yml", "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        subprocess.run(
            ["ansible-vault", "encrypt", "/tmp/all.yml", "--vault-password-file", vault_pass_file, "--output", vault_path],
            check=True
        )
        os.remove("/tmp/all.yml")
        return HTMLResponse("<h2>Configuration terminée. Redéploiement de Traefik...</h2>")
    except Exception as e:
        return HTMLResponse(f"Erreur étape 4 : {e}", status_code=500)
