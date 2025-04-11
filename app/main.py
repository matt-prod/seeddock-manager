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

def update_vault_section(section_data: dict):
    try:
        result = subprocess.run(
            ["ansible-vault", "view", VAULT_REL_PATH, "--vault-password-file", VAULT_PASS_REL_PATH],
            cwd=SDM_ROOT, capture_output=True, text=True, check=True
        )
        vault = yaml.safe_load(result.stdout) or {}
        vault.update(section_data)

        tmp = "/tmp/all.yml"
        with open(tmp, "w") as f:
            yaml.dump(vault, f, default_flow_style=False)

        subprocess.run(
            ["ansible-vault", "encrypt", tmp, "--vault-password-file", VAULT_PASS_REL_PATH,
             "--output", VAULT_REL_PATH, "--encrypt-vault-id", "default"],
            cwd=SDM_ROOT,
            check=True
        )
        os.remove(tmp)
        return True
    except Exception as e:
        return str(e)


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
                        ["ansible-vault", "encrypt", VAULT_REL_PATH,
                         "--vault-password-file", VAULT_PASS_REL_PATH,
                         "--encrypt-vault-id", "default"],
                        cwd=SDM_ROOT, check=True
                    )
        except Exception as e:
            return HTMLResponse(f"Erreur lors du chiffrement initial : {e}", status_code=500)
    return templates.TemplateResponse("step1.html", {"request": request})

@app.post("/step1")
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    return RedirectResponse("/step1_success", status_code=302) if update_vault_section({
        "user": {"name": username, "password": password},
        "account": {"admin": 1}
    }) is True else HTMLResponse("Erreur step1", status_code=500)

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
    return RedirectResponse("/step3", status_code=302) if update_vault_section({
        "network": {"ipv6": enable_ipv6 == "on"}
    }) is True else HTMLResponse("Erreur étape 2", status_code=500)


# === STEP 3 : route principale ===
@app.get("/step3", response_class=HTMLResponse)
async def step3(request: Request):
    return templates.TemplateResponse("step3.html", {"request": request})

@app.post("/step3")
async def handle_step3(request: Request, domain_enabled: str = Form(...), domain_name: str = Form(""), provider: str = Form("")):
    ok = update_vault_section({
        "domain": {
            "enabled": domain_enabled == "yes",
            "name": domain_name,
            "provider": provider
        }
    })
    if ok is not True:
        return HTMLResponse("Erreur vault step3", status_code=500)
    return RedirectResponse(f"/step3/{provider}", status_code=302) if domain_enabled == "yes" else RedirectResponse("/step4", status_code=302)


# === STEP 3 PROVIDERS ===
@app.get("/step3/cloudflare", response_class=HTMLResponse)
async def step3_cf_form(request: Request):
    return templates.TemplateResponse("step3_cloudflare.html", {"request": request})

@app.post("/step3/cloudflare")
async def step3_cf_submit(request: Request, email: str = Form(...), api_key: str = Form(...)):
    return RedirectResponse("/step4", status_code=302) if update_vault_section({
        "cloudflare": {"email": email, "api_key": api_key}
    }) is True else HTMLResponse("Erreur Cloudflare", status_code=500)

@app.get("/step3/hetzner", response_class=HTMLResponse)
async def step3_hetzner_form(request: Request):
    return templates.TemplateResponse("step3_hetzner.html", {"request": request})

@app.post("/step3/hetzner")
async def step3_hetzner_submit(request: Request, api_token: str = Form(...)):
    return RedirectResponse("/step4", status_code=302) if update_vault_section({
        "hetzner": {"api_token": api_token}
    }) is True else HTMLResponse("Erreur Hetzner", status_code=500)

@app.get("/step3/rfc2136", response_class=HTMLResponse)
async def step3_rfc2136_form(request: Request):
    return templates.TemplateResponse("step3_rfc2136.html", {"request": request})

@app.post("/step3/rfc2136")
async def step3_rfc2136_submit(request: Request, server: str = Form(...), key_name: str = Form(...), key_secret: str = Form(...)):
    return RedirectResponse("/step4", status_code=302) if update_vault_section({
        "rfc2136": {
            "server": server,
            "key_name": key_name,
            "key_secret": key_secret
        }
    }) is True else HTMLResponse("Erreur RFC2136", status_code=500)

@app.get("/step3/powerdns", response_class=HTMLResponse)
async def step3_powerdns_form(request: Request):
    return templates.TemplateResponse("step3_powerdns.html", {"request": request})

@app.post("/step3/powerdns")
async def step3_powerdns_submit(request: Request, api_url: str = Form(...), api_token: str = Form(...)):
    return RedirectResponse("/step4", status_code=302) if update_vault_section({
        "powerdns": {
            "api_url": api_url,
            "api_token": api_token
        }
    }) is True else HTMLResponse("Erreur PowerDNS", status_code=500)


# === STEP 4 ===
@app.get("/step4", response_class=HTMLResponse)
async def step4(request: Request):
    return templates.TemplateResponse("step4.html", {"request": request})

@app.post("/step4")
async def handle_step4(request: Request, email: str = Form(...)):
    return HTMLResponse("<h2>Configuration terminée. Redéploiement de Traefik…</h2>") if update_vault_section({
        "certbot": {"email": email}
    }) is True else HTMLResponse("Erreur étape 4", status_code=500)
