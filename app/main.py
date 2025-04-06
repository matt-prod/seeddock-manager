from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import subprocess
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")

def get_logo_output():
    logo_script = "/srv/sdm/includes/logo.sh"
    variables_script = "/srv/sdm/includes/variables.sh"

    if not os.path.exists(logo_script):
        return "[ERREUR] Fichier logo.sh introuvable"

    try:
        result = subprocess.run(
            ["bash", "-c", f"source {variables_script} && source {logo_script} && show_logo"],
            capture_output=True,
            text=True,
            timeout=2
        )
        raw_output = result.stdout if result.returncode == 0 else "[ERREUR] Impossible d'afficher le logo"
    except Exception as e:
        return f"[Exception] {str(e)}"

    conv = Ansi2HTMLConverter(inline=True, scheme='xterm')
    return conv.convert(raw_output, full=False)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logo_content = get_logo_output()
    return templates.TemplateResponse("index.html", {"request": request, "logo": logo_content})


@app.get("/step1", response_class=HTMLResponse)
async def step1_form(request: Request):
    return templates.TemplateResponse("step1.html", {"request": request})


@app.post("/step1")
async def step1_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    vault_pass_path = "/srv/sdm/vault_pass"
    vault_file_path = "/srv/sdm/group_vars/all.yml"

    def encrypt_string(value):
        cmd = [
            "ansible-vault", "encrypt_string",
            "--vault-password-file", vault_pass_path,
            value,
            "--name", "dummy"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()

    encrypted_username = encrypt_string(username).replace("dummy", "user.name")
    encrypted_password = encrypt_string(password).replace("dummy", "user.password")

    # Read and filter existing
    if os.path.exists(vault_file_path):
        with open(vault_file_path, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    lines = [line for line in lines if not line.strip().startswith("user.")]
    lines.append(encrypted_username + "\n")
    lines.append(encrypted_password + "\n")

    with open(vault_file_path, "w") as f:
        f.writelines(lines)

    return RedirectResponse("/", status_code=303)
