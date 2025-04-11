from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os
import yaml
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

# === CHEMINS CENTRALISÉS ===
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
        try:
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
        except Exception as e:
            return HTMLResponse(f"Erreur lors du chiffrement initial : {e}", status_code=500)

    return templates.TemplateResponse("step1.html", {"request": request})


@app.post("/step1")
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT,
            capture_output=True, text=True, check=True
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


# === STEP 2 : IPv6 ===
@app.get("/step2", response_class=HTMLResponse)
async def step2(request: Request):
    return templates.TemplateResponse("step2.html", {"request": request})


@app.post("/step2")
async def handle_step2(request: Request, enable_ipv6: str = Form(...)):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT,
            capture_output=True, text=True, check=True
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

    except Exception as e:
        return HTMLResponse(f"Erreur étape 2 : {e}", status_code=500)


# === STEP 3 : Domaine et provider ===
@app.get("/step3", response_class=HTMLResponse)
async def step3(request: Request):
    return templates.TemplateResponse("step3.html", {"request": request})


@app.post("/step3")
async def handle_step3(request: Request, domain_enabled: str = Form(...), domain_name: str = Form(""), provider: str = Form("")):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT,
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
            [
                "ansible-vault", "encrypt", "/tmp/all.yml",
                "--vault-password-file", VAULT_PASS_REL_PATH,
                "--output", VAULT_REL_PATH,
                "--encrypt-vault-id", "default"
            ],
            cwd=SDM_ROOT,
            check=True
        )
        os.remove("/tmp/all.yml")

        if domain_enabled == "yes" and provider:
            return RedirectResponse(f"/step3/{provider}", status_code=302)
        return RedirectResponse("/step4", status_code=302)

    except Exception as e:
        return HTMLResponse(f"Erreur étape 3 : {e}", status_code=500)

@app.post("/step3/cloudflare")
async def step3_cloudflare_post(
    request: Request,
    email: str = Form(...),
    api_key: str = Form(...)
):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT, capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["dns_provider_config"] = {
            "cloudflare": {
                "email": email,
                "api_key": api_key
            }
        }

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
            cwd=SDM_ROOT, check=True
        )
        os.remove(tmp_path)
        return RedirectResponse("/step4", status_code=302)

    except Exception as e:
        return HTMLResponse(f"Erreur Cloudflare POST : {e}", status_code=500)

@app.post("/step3/hetzner")
async def step3_hetzner_post(
    request: Request,
    api_token: str = Form(...)
):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT, capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["dns_provider_config"] = {
            "hetzner": {
                "api_token": api_token
            }
        }

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
            cwd=SDM_ROOT, check=True
        )
        os.remove(tmp_path)
        return RedirectResponse("/step4", status_code=302)

    except Exception as e:
        return HTMLResponse(f"Erreur Hetzner POST : {e}", status_code=500)

@app.post("/step3/powerdns")
async def step3_powerdns_post(
    request: Request,
    api_url: str = Form(...),
    api_token: str = Form(...)
):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT, capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["dns_provider_config"] = {
            "powerdns": {
                "api_url": api_url,
                "api_token": api_token
            }
        }

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
            cwd=SDM_ROOT, check=True
        )
        os.remove(tmp_path)
        return RedirectResponse("/step4", status_code=302)

    except Exception as e:
        return HTMLResponse(f"Erreur PowerDNS POST : {e}", status_code=500)

@app.post("/step3/rfc2136")
async def step3_rfc2136_post(
    request: Request,
    server: str = Form(...),
    key_name: str = Form(...),
    key_secret: str = Form(...)
):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT, capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["dns_provider_config"] = {
            "rfc2136": {
                "server": server,
                "key_name": key_name,
                "key_secret": key_secret
            }
        }

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
            cwd=SDM_ROOT, check=True
        )
        os.remove(tmp_path)
        return RedirectResponse("/step4", status_code=302)

    except Exception as e:
        return HTMLResponse(f"Erreur RFC2136 POST : {e}", status_code=500)

# === STEP 4 : Certbot Email ===
@app.get("/step4", response_class=HTMLResponse)
async def step4(request: Request):
    return templates.TemplateResponse("step4.html", {"request": request})


@app.post("/step4")
async def handle_step4(request: Request, email: str = Form(...)):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT,
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout) or {}
        data["certbot"] = {"email": email}

        with open("/tmp/all.yml", "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        subprocess.run(
            [
                "ansible-vault", "encrypt", "/tmp/all.yml",
                "--vault-password-file", VAULT_PASS_REL_PATH,
                "--output", VAULT_REL_PATH,
                "--encrypt-vault-id", "default"
            ],
            cwd=SDM_ROOT,
            check=True
        )

        os.remove("/tmp/all.yml")
        return HTMLResponse("<h2>Configuration terminée. Redéploiement de Traefik...</h2>")

    except Exception as e:
        return HTMLResponse(f"Erreur étape 4 : {e}", status_code=500)
