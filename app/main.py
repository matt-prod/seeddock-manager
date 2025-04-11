from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os
import yaml
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

# --- Chemins ---
vault_path = "/srv/sdm/SeedDock/SDM/group_vars/all.yml"
vault_pass_file = "/srv/sdm/config/vault_pass"
logo_script = "/srv/sdm/includes/logo.sh"
variables_script = "/srv/sdm/includes/variables.sh"

# --- Logo ---
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

# --- Helper Vault ---
def read_vault():
    if not os.path.exists(vault_pass_file):
        raise FileNotFoundError("vault_pass manquant")
    result = subprocess.run(
        ["ansible-vault", "view", vault_path, "--vault-password-file", vault_pass_file],
        capture_output=True, text=True, check=True
    )
    return yaml.safe_load(result.stdout) or {}

def write_vault(data: dict):
    tmp_file = "/tmp/all.yml"
    with open(tmp_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    subprocess.run(
        ["ansible-vault", "encrypt", tmp_file, "--vault-password-file", vault_pass_file, "--output", vault_path],
        check=True
    )
    os.remove(tmp_file)

# --- Accueil ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logo = get_logo_output()
    return templates.TemplateResponse("index.html", {"request": request, "logo": logo})

# --- Étape 1 ---
@app.get("/step1", response_class=HTMLResponse)
async def show_step1(request: Request):
    return templates.TemplateResponse("step1.html", {"request": request})

@app.post("/step1")
async def handle_step1(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        data = read_vault()
        data["user"] = {"name": username, "password": password}
        data["account"] = {"admin": 1}
        write_vault(data)
        return RedirectResponse("/step1_success", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

@app.get("/step1_success", response_class=HTMLResponse)
async def step1_success(request: Request):
    return HTMLResponse("""
    <html><body>
    <h2>✅ Compte admin créé avec succès</h2>
    <a href="/step2">Continuer</a>
    </body></html>
    """)

# --- Étape 2 (IP / IPv6) ---
@app.get("/step2", response_class=HTMLResponse)
async def show_step2(request: Request):
    return templates.TemplateResponse("step2.html", {"request": request})

@app.post("/step2")
async def handle_step2(request: Request, ipv6_enabled: str = Form("no")):
    try:
        data = read_vault()
        data["network"] = {"ipv6": ipv6_enabled == "yes"}
        write_vault(data)
        return RedirectResponse("/step3", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

# --- Étape 3 (Choix DNS) ---
@app.get("/step3", response_class=HTMLResponse)
async def show_step3(request: Request):
    return templates.TemplateResponse("step3.html", {"request": request})

@app.post("/step3")
async def handle_step3(request: Request, use_domain: str = Form("no"), provider: str = Form(None)):
    try:
        data = read_vault()
        data["dns"] = {"use_domain": use_domain == "yes", "provider": provider}
        write_vault(data)
        if use_domain == "yes" and provider:
            return RedirectResponse(f"/step3/{provider}", status_code=302)
        else:
            return RedirectResponse("/step4", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

# --- Sous-étapes pour chaque provider ---
@app.get("/step3/cloudflare", response_class=HTMLResponse)
async def step3_cloudflare(request: Request):
    return templates.TemplateResponse("step3_cloudflare.html", {"request": request})

@app.post("/step3/cloudflare")
async def handle_step3_cloudflare(request: Request, email: str = Form(...), api_key: str = Form(...)):
    try:
        data = read_vault()
        data["dns"]["cloudflare"] = {"email": email, "api_key": api_key}
        write_vault(data)
        return RedirectResponse("/step4", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

@app.get("/step3/powerdns", response_class=HTMLResponse)
async def step3_powerdns(request: Request):
    return templates.TemplateResponse("step3_powerdns.html", {"request": request})

@app.post("/step3/powerdns")
async def handle_step3_powerdns(request: Request, api_url: str = Form(...), api_token: str = Form(...)):
    try:
        data = read_vault()
        data["dns"]["powerdns"] = {"api_url": api_url, "api_token": api_token}
        write_vault(data)
        return RedirectResponse("/step4", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

@app.get("/step3/hetzner", response_class=HTMLResponse)
async def step3_hetzner(request: Request):
    return templates.TemplateResponse("step3_hetzner.html", {"request": request})

@app.post("/step3/hetzner")
async def handle_step3_hetzner(request: Request, api_token: str = Form(...)):
    try:
        data = read_vault()
        data["dns"]["hetzner"] = {"api_token": api_token}
        write_vault(data)
        return RedirectResponse("/step4", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

@app.get("/step3/rfc2136", response_class=HTMLResponse)
async def step3_rfc2136(request: Request):
    return templates.TemplateResponse("step3_rfc2136.html", {"request": request})

@app.post("/step3/rfc2136")
async def handle_step3_rfc2136(request: Request,
                                server: str = Form(...),
                                key_name: str = Form(...),
                                key_secret: str = Form(...)):
    try:
        data = read_vault()
        data["dns"]["rfc2136"] = {
            "server": server,
            "key_name": key_name,
            "key_secret": key_secret
        }
        write_vault(data)
        return RedirectResponse("/step4", status_code=302)
    except Exception as e:
        return HTMLResponse(f"Erreur : {str(e)}", status_code=500)

@app.get("/step4", response_class=HTMLResponse)
async def show_step4(request: Request):
    return templates.TemplateResponse("step4.html", {"request": request})

@app.post("/step4")
async def deploy_traefik_prod(request: Request):
    try:
        # Déchiffrer vault
        result = subprocess.run(
            ["ansible-vault", "view", vault_path, "--vault-password-file", vault_pass_file],
            capture_output=True, text=True, check=True
        )
        data = yaml.safe_load(result.stdout)

        ipv4 = data.get("network", {}).get("ipv4", "")
        ipv6_enabled = data.get("network", {}).get("ipv6_enabled", False)
        ipv6 = data.get("network", {}).get("ipv6", "")
        ula_prefix = data.get("network", {}).get("ula_prefix", "")
        domain = data.get("domain", {}).get("name", "")
        dns_provider = data.get("domain", {}).get("provider", "")
        email = data.get("domain", {}).get("email", "")
        challenge = "dnsChallenge" if dns_provider != "none" else "httpChallenge"

        # Chemin des fichiers
        dynamic_dir = "/srv/sdm/containers/traefik/dynamic"
        os.makedirs(dynamic_dir, exist_ok=True)
        traefik_config = f"""
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    {challenge}:
      {'provider: ' + dns_provider if challenge == 'dnsChallenge' else 'entryPoint: web'}
    email: "{email}"
    storage: "/certs/acme.json"

providers:
  docker:
    exposedByDefault: false
"""

        config_path = "/srv/sdm/containers/traefik/config/traefik.yml"
        with open(config_path, "w") as f:
            f.write(traefik_config)

        # (Re)déploiement du conteneur traefik_prod
        subprocess.run(["docker", "rm", "-f", "traefik_prod"], stderr=subprocess.DEVNULL)
        cmd = [
            "docker", "run", "-d", "--name", "traefik_prod",
            "--restart", "unless-stopped",
            "--network", "traefik",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "-v", "/srv/sdm/containers/traefik/config:/etc/traefik",
            "-v", "/srv/sdm/containers/traefik/config/certs:/certs",
            "-p", "80:80", "-p", "443:443",
            "traefik:v3.0"
        ]

        subprocess.run(cmd, check=True)

        return HTMLResponse("""
        <html><body style='text-align: center; font-family: Arial;'>
        <h2>✅ Traefik de production déployé avec succès !</h2>
        <a href="/final">Terminer</a>
        </body></html>
        """)

    except Exception as e:
        return HTMLResponse(content=f"Erreur lors du déploiement : {str(e)}", status_code=500)
