from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os
import yaml
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

# === PATH CONFIGURATION ===
SDM_ROOT = "/srv/sdm"
VAULT_REL_PATH = "./group_vars/all.yml"
VAULT_PASS_REL_PATH = "./config/vault_pass"
LOGO_SCRIPT = os.path.join(SDM_ROOT, "includes", "logo.sh")
VARIABLES_SCRIPT = os.path.join(SDM_ROOT, "includes", "variables.sh")

def get_logo_output():
    if not os.path.exists(LOGO_SCRIPT):
        return "[ERREUR] Fichier logo.sh introuvable"
    try:
        result = subprocess.run(
            ["bash", "-c", f"source {VARIABLES_SCRIPT} && source {LOGO_SCRIPT} && show_logo"],
            capture_output=True, text=True, timeout=2
        )
        return Ansi2HTMLConverter().convert(result.stdout, full=False) if result.returncode == 0 else "[ERREUR] Impossible d'afficher le logo"
    except Exception as e:
        return f"[Exception] {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logo = get_logo_output()
    return templates.TemplateResponse("index.html", {"request": request, "logo": logo})

# === STEP 1 ===
@app.get("/step1", response_class=HTMLResponse)
async def show_step1(request: Request):
    vault_path = os.path.join(SDM_ROOT, VAULT_REL_PATH)
    vault_pass_file = os.path.join(SDM_ROOT, VAULT_PASS_REL_PATH)

    if os.path.exists(vault_path) and os.path.exists(vault_pass_file):
        with open(vault_path, "r") as f:
            first_line = f.readline().strip()
            if not first_line.startswith("$ANSIBLE_VAULT"):
                subprocess.run(
                    [
                        "ansible-vault", "encrypt", VAULT_REL_PATH,
                        "--vault-password-file", VAULT_PASS_REL_PATH,
                        "--encrypt-vault-id", "default"
                    ],
                    cwd=SDM_ROOT,
                    check=True
                )
    return templates.TemplateResponse("step1.html", {"request": request})

@app.post("/step1")
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    result = subprocess.run(
        ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
        cwd=SDM_ROOT, capture_output=True, text=True, check=True
    )
    data = yaml.safe_load(result.stdout) or {}
    data["user"] = {"name": username, "password": password}
    data["account"] = {"admin": 1}

    tmp_path = "/tmp/all.yml"
    with open(tmp_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    subprocess.run(
        [
            "ansible-vault", "encrypt", tmp_path,
            "--vault-password-file", VAULT_PASS_REL_PATH,
            "--output", VAULT_REL_PATH,
            "--encrypt-vault-id", "default"
        ],
        cwd=SDM_ROOT,
        check=True
    )

    os.remove(tmp_path)
    return RedirectResponse("/step1_success", status_code=302)

@app.get("/step1_success", response_class=HTMLResponse)
async def step1_success(request: Request):
    return HTMLResponse("""
    <html><body style='text-align: center; font-family: Arial;'>
    <h2>Compte admin créé avec succès.</h2>
    <a href="/step2">Suivant</a>
    </body></html>
    """)

# === STEP 2 ===
@app.get("/step2", response_class=HTMLResponse)
async def step2(request: Request):
    return templates.TemplateResponse("step2.html", {"request": request})

@app.post("/step2")
async def handle_step2(request: Request, enable_ipv6: str = Form(...)):
    result = subprocess.run(
        ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
        cwd=SDM_ROOT, capture_output=True, text=True, check=True
    )
    data = yaml.safe_load(result.stdout) or {}
    data["network"] = {"ipv6": enable_ipv6 == "on"}

    tmp_path = "/tmp/all.yml"
    with open(tmp_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    subprocess.run(
        [
            "ansible-vault", "encrypt", tmp_path,
            "--vault-password-file", VAULT_PASS_REL_PATH,
            "--output", VAULT_REL_PATH,
            "--encrypt-vault-id", "default"
        ],
        cwd=SDM_ROOT,
        check=True
    )

    os.remove(tmp_path)
    return RedirectResponse("/step3", status_code=302)

# === STEP 3 (Domaine principal) ===
@app.get("/step3", response_class=HTMLResponse)
async def step3(request: Request):
    return templates.TemplateResponse("step3.html", {"request": request})

@app.post("/step3_{provider}")
async def provider_handler(request: Request, provider: str):
    form = await request.form()
    form_data = {key: form.get(key) for key in form.keys()}

    result = subprocess.run(
        ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
        cwd=SDM_ROOT, capture_output=True, text=True, check=True
    )
    data = yaml.safe_load(result.stdout) or {}
    data["provider_config"] = {provider: form_data}

    tmp_path = "/tmp/all.yml"
    with open(tmp_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    subprocess.run(
        [
            "ansible-vault", "encrypt", tmp_path,
            "--vault-password-file", VAULT_PASS_REL_PATH,
            "--output", VAULT_REL_PATH,
            "--encrypt-vault-id", "default"
        ],
        cwd=SDM_ROOT,
        check=True
    )

    os.remove(tmp_path)
    return RedirectResponse("/step4", status_code=302)

# === STEP 3.x : provider spécifiques
@app.get("/step3_{provider}", response_class=HTMLResponse)
async def provider_form(request: Request, provider: str):
    template_name = f"step3_{provider}.html"
    return templates.TemplateResponse(template_name, {"request": request})

@app.post("/step3_{provider}")
async def provider_handler(request: Request, provider: str, **form_data):
    result = subprocess.run(
        ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
        cwd=SDM_ROOT, capture_output=True, text=True, check=True
    )
    data = yaml.safe_load(result.stdout) or {}
    data["provider_config"] = {provider: form_data}

    tmp_path = "/tmp/all.yml"
    with open(tmp_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    subprocess.run(
        [
            "ansible-vault", "encrypt", tmp_path,
            "--vault-password-file", VAULT_PASS_REL_PATH,
            "--output", VAULT_REL_PATH,
            "--encrypt-vault-id", "default"
        ],
        cwd=SDM_ROOT,
        check=True
    )

    os.remove(tmp_path)
    return RedirectResponse("/step4", status_code=302)

# === STEP 4 ===
@app.get("/step4", response_class=HTMLResponse)
async def step4(request: Request):
    return templates.TemplateResponse("step4.html", {"request": request})

@app.post("/step4")
async def handle_step4(request: Request, email: str = Form(...)):
    result = subprocess.run(
        ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
        cwd=SDM_ROOT, capture_output=True, text=True, check=True
    )
    data = yaml.safe_load(result.stdout) or {}
    data["certbot"] = {"email": email}

    tmp_path = "/tmp/all.yml"
    with open(tmp_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    subprocess.run(
        [
            "ansible-vault", "encrypt", tmp_path,
            "--vault-password-file", VAULT_PASS_REL_PATH,
            "--output", VAULT_REL_PATH,
            "--encrypt-vault-id", "default"
        ],
        cwd=SDM_ROOT,
        check=True
    )

    os.remove(tmp_path)
    return HTMLResponse("<h2>✅ Configuration terminée. Redéploiement de Traefik en cours...</h2>")
