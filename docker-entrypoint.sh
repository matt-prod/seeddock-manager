#!/bin/bash
set -e

echo "[SDM] Démarrage du conteneur..."
echo "[SDM] Chemin Ansible : /srv/sdm"

if [ ! -f /srv/sdm/ansible.cfg ]; then
  echo "[SDM] ❌ Fichier ansible.cfg introuvable dans /srv/sdm"
  exit 1
fi

exec python3 -m app
