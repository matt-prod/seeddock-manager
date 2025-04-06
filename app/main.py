from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import os

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
        return result.stdout if result.returncode == 0 else "[ERREUR] Impossible d'afficher le logo"
    except Exception as e:
        return f"[Exception] {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logo_content = get_logo_output()
    return templates.TemplateResponse("step1.html", {"request": request, "logo": logo_content})

@app.post("/step1")
async def step1_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    vault_file = "/srv/sdm/group_vars/all.yml"
    vault_pass_file = "/vault_pass"

    for key, value in [("sdm_admin_user", username), ("sdm_admin_pass", password)]:
        cmd = [
            "ansible-vault", "encrypt_string", value,
            "--name", key,
            "--vault-password-file", vault_pass_file
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                with open(vault_file, "a") as f:
                    f.write(result.stdout + "\n")
            else:
                return HTMLResponse(f"Erreur de chiffrement: {result.stderr}", status_code=500)
        except Exception as e:
            return HTMLResponse(f"Exception: {str(e)}", status_code=500)

    return RedirectResponse(url="/step2", status_code=303)
