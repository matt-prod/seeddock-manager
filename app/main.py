from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from subprocess import check_output, CalledProcessError
from ansi2html import Ansi2HTMLConverter

app = FastAPI()
templates = Jinja2Templates(directory="/app/templates")
conv = Ansi2HTMLConverter(inline=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logo_path = "/srv/sdm/includes/logo.sh"
    logo_rendered = ""

    try:
        # Récupération et exécution du script bash complet
        logo_rendered = check_output(["bash", "-c", f"source {logo_path} && show_logo"], text=True)
    except CalledProcessError as e:
        logo_rendered = f"Erreur lors de l'exécution du script : {e}"

    # Conversion ANSI vers HTML pour préserver les couleurs du terminal
    logo_html = conv.convert(logo_rendered, full=False)

    return templates.TemplateResponse("index.html", {"request": request, "logo": logo_html})
