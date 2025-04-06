# SeedDock Manager (SDM)

SeedDock Manager est l’interface web compagnon de SeedDock. Il permet la configuration post-installation via un assistant web, le tout basé sur FastAPI et Ansible.

## Fonctionnalités

- Affichage dynamique du logo et des infos système
- Assistant web de configuration (wizard)
- Écriture dans un vault Ansible chiffré
- Gestion d’un catalogue d’applications déployables via Ansible

## Stack

- Python 3.11
- FastAPI + Jinja2
- Docker (image disponible sur GHCR)
- Ansible (intégré dans le futur)

## Développement

```bash
docker build -t sdm .
docker run -d -p 8000:8000 -v $(pwd)/includes:/srv/sdm/includes sdm
```

## Déploiement (via SeedDock)

Le conteneur est automatiquement lancé avec :

- Accès Web via Traefik
- Volume partagé avec `includes/` de SeedDock
- Fichiers vault (`vault_pass`, `group_vars/all.yml`)

## Licence

Voir [LICENSE](LICENSE).
