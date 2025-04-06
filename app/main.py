from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import subprocess

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
        return result.stdout if result.returncode == 0 else "[ERREUR] Impossible d'afficher le logo"
    except Exception as e:
        return f"[Exception] {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logo_content = get_logo_output()
    return templates.TemplateResponse("index.html", {"request": request, "logo": logo_content})

@app.post("/step1")
async def handle_step1(username: str = Form(...), password: str = Form(...)):
    # Stockage chiffré dans le vault via ansible-vault
    vault_path = "/srv/sdm/vault/group_vars/all.yml"
    vault_pass_path = "/srv/sdm/vault/vault_pass"

    if not os.path.exists(vault_path):
        os.makedirs(os.path.dirname(vault_path), exist_ok=True)
        with open(vault_path, "w") as f:
            f.write("")

    try:
        playbook_content = f"""
        - hosts: localhost
          gather_facts: no
          tasks:
            - name: Enregistrer les identifiants admin
              ansible.builtin.include_vars:
                file: "{vault_path}"
                name: secrets

            - name: Définir les credentials
              ansible.builtin.set_fact:
                secrets:
                  admin_user: "{username}"
                  admin_pass: "{password}"

            - name: Sauvegarder les variables dans le vault
              copy:
                content: "{{{{ secrets | to_nice_yaml }}}}"
                dest: "{vault_path}"
        """

        with open("/tmp/step1.yml", "w") as f:
            f.write(playbook_content)

        subprocess.run([
            "ansible-playbook", "/tmp/step1.yml",
            "--vault-password-file", vault_pass_path
        ], check=True)
    except Exception as e:
        return HTMLResponse(f"<h1>Erreur : {str(e)}</h1>", status_code=500)

    return RedirectResponse(url="/step2", status_code=303)
