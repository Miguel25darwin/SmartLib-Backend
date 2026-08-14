# SmartLib Backend — API REST FastAPI

Backend du système de gestion de bibliothèque universitaire **SmartLib**.
Développé avec **FastAPI**, **PostgreSQL** et **SQLAlchemy 2.0**, conforme au Cahier d'Architecture SmartLib v1.0.

---

## Stack technique

| Composant       | Technologie                        |
|-----------------|------------------------------------|
| Framework API   | FastAPI 0.115                      |
| ORM             | SQLAlchemy 2.0 (mode `Mapped`)     |
| Base de données | PostgreSQL 16                      |
| Migrations      | Alembic 1.13                       |
| Auth            | JWT (python-jose) + bcrypt         |
| Validation      | Pydantic v2                        |
| Serveur ASGI    | Uvicorn                            |
| Conteneurisation| Docker + Docker Compose            |
| Tests           | pytest + httpx + pytest-cov        |

---

## Etat d'avancement

- [x] 1. Mise en place de l'environnement (venv, dépendances, structure de projet)
- [x] 2. Configuration (`app/core/config.py`, `.env`, `app/core/security.py`)
- [x] 3. Modèles SQLAlchemy (`users`, `books`, `copies`, `digital_resources`, `loans`) avec enums métier
- [x] 4. Schémas Pydantic (Create / Read / Update) pour toutes les entités
- [x] 5. Migrations Alembic (autogénération + `alembic upgrade head`)
- [x] 6. Module Auth : inscription (`POST /auth/register`), connexion (`POST /auth/login`), profil (`GET /users/me`)
- [x] 7. Module Catalogue : CRUD livres + gestion exemplaires, RBAC bibliothécaire/admin
- [x] 8. Module Emprunts : emprunt, retour, historique, règles métier (quota, disponibilité, durée)
- [x] 9. Module Rapports : livres les plus empruntés, utilisateurs actifs, statistiques de retard, tableau de bord
- [x] 10. Suite de tests pytest (auth, catalogue, emprunts) avec isolation transactionnelle par test
- [x] 11. Dockerisation complète : `Dockerfile` + `docker-compose.yml` (migration automatique au démarrage)

---

## Lancer en développement (local)

### Prérequis

- Python 3.12+ avec environnement virtuel activé
- PostgreSQL accessible sur `localhost:5432` avec l'utilisateur `smartlib_user`

### Démarrage

```bash
# 1. Activer le venv
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Appliquer les migrations
alembic upgrade head

# 4. Lancer le serveur (mode rechargement automatique)
uvicorn app.main:app --reload
```

L'API est disponible sur : http://localhost:8000/api/v1/docs

---

## Lancer avec Docker (recommandé pour une démo complète)

```bash
docker compose up --build
```

L'API est alors disponible sur http://localhost:8000/api/v1/docs

La migration Alembic est appliquée automatiquement au démarrage du conteneur `api`.

---

## Peupler la base avec des donnees de demonstration

Cree des comptes de test (un par role) et un catalogue de 5 livres avec exemplaires :

```bash
python scripts/seed.py
```

Mot de passe commun a tous les comptes crees : SmartLib2026!

Comptes crees :
- admin@smartlib.cm (admin)
- bibliothecaire@smartlib.cm (librarian)
- enseignant@smartlib.cm (lecturer)
- personnel@smartlib.cm (staff)
- etudiant1@smartlib.cm, etudiant2@smartlib.cm, etudiant3@smartlib.cm (student)

Le script est idempotent sur les comptes (relancer ne duplique pas les utilisateurs
existants) mais ajoute toujours de nouveaux livres si relance plusieurs fois.

---

## Lancer les tests

Nécessite une base PostgreSQL de test nommée `smartlib_test_db` :

```bash
docker exec -it smartlib-postgres psql -U smartlib_user -c "CREATE DATABASE smartlib_test_db OWNER smartlib_user;"
pip install -r requirements-dev.txt
pytest -v --cov=app tests/
```

### A. Créer la base de test et lancer la suite pytest

```bash
docker exec -it smartlib-postgres psql -U smartlib_user -c "CREATE DATABASE smartlib_test_db OWNER smartlib_user;"
pip install -r requirements-dev.txt
pytest -v tests/
```

### B. Arrêter proprement l'environnement actuel puis valider le démarrage 100% Docker (API + DB ensemble, migration automatique)

```bash
docker stop smartlib-postgres
docker compose up --build -d
sleep 5
curl -s http://localhost:8000/health
```

---

> **Note Phase 1 :** On s'arrête strictement là — c'est la dernière étape du prototype Phase 1.
> Phase 2 prévoira : tâches planifiées (bascule `ACTIVE → OVERDUE`), cache Redis, notifications e-mail, et optimisations de requêtes (vues matérialisées).

---

## Structure du projet

```
SmartLib-Backend/
├── app/
│   ├── core/           # config, sécurité, dépendances FastAPI
│   ├── db/             # session SQLAlchemy, classe de base ORM
│   ├── models/         # entités SQLAlchemy + enums métier
│   ├── schemas/        # schémas Pydantic (Create/Read/Update)
│   ├── routers/        # endpoints FastAPI (auth, books, loans, reports, users)
│   ├── services/       # logique métier découplée des routers
│   └── main.py         # point d'entrée FastAPI
├── alembic/            # migrations de base de données
├── tests/              # suite pytest (conftest + test_auth/books/loans)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── alembic.ini
```

---

## Variables d'environnement

| Variable                             | Description                             | Exemple                          |
|--------------------------------------|-----------------------------------------|----------------------------------|
| `DATABASE_URL`                       | URL de connexion SQLAlchemy             | `postgresql+psycopg2://...`      |
| `JWT_SECRET_KEY`                     | Clé secrète de signature JWT            | chaîne aléatoire longue          |
| `JWT_ALGORITHM`                      | Algorithme JWT                          | `HS256`                          |
| `ACCESS_TOKEN_EXPIRE_MINUTES_CAMPUS` | Durée du jeton (accès campus)           | `480`                            |
| `ACCESS_TOKEN_EXPIRE_MINUTES_REMOTE` | Durée du jeton (accès distant)          | `120`                            |
| `APP_ENV`                            | Environnement applicatif                | `development` / `production`     |

Copier `.env.example` vers `.env` et adapter les valeurs avant le premier lancement.
