# Diagramme Entité-Association — Gestion du catalogue SmartLib

> Source de vérité : modèles SQLAlchemy (`app/models/`) + migrations Alembic.
> SGBD : PostgreSQL 16. Rendu : [mermaid.live](https://mermaid.live) ou aperçu Markdown GitHub/GitLab.

```mermaid
erDiagram
    BOOKS ||--o{ COPIES : "possede"
    BOOKS ||--o{ DIGITAL_RESOURCES : "possede"
    COPIES ||--o{ LOANS : "est emprunte"
    DIGITAL_RESOURCES ||--o{ LOANS : "est empruntee"
    USERS ||--o{ LOANS : "effectue"

    BOOKS {
        int id PK "auto-increment"
        varchar title_fr "nullable, 500"
        varchar title_en "nullable, 500"
        varchar author "NOT NULL, indexe"
        varchar isbn "UNIQUE, nullable, 20"
        varchar publisher "nullable, 255"
        int publication_year "nullable"
        varchar dewey_classification "nullable, 10, indexe"
        book_type type "PHYSICAL ou DIGITAL"
        book_language language "FR ou EN, defaut FR"
        varchar cover_url "nullable, 500"
        timestamp created_at
        timestamp updated_at
    }

    COPIES {
        int id PK
        int book_id FK "ON DELETE CASCADE"
        copy_status status "AVAILABLE BORROWED RESERVED DAMAGED LOST, defaut AVAILABLE"
        varchar location "nullable, 100 (rayon cote)"
        varchar qr_code "UNIQUE NOT NULL, format BK-XXXXXXXX"
    }

    DIGITAL_RESOURCES {
        int id PK
        int book_id FK "ON DELETE CASCADE"
        varchar file_url "NOT NULL, 500"
        digital_format format "PDF EPUB AUDIO VIDEO"
    }

    USERS {
        uuid id PK
        varchar full_name "NOT NULL"
        varchar email "UNIQUE, indexe"
        varchar password_hash "NOT NULL"
        user_role role "STUDENT LECTURER STAFF LIBRARIAN ADMIN"
        varchar card_number "UNIQUE, format PREFIX-ANNEE-NNNNN"
        language_pref language_pref "FR ou EN"
        boolean is_active "defaut true"
        timestamp created_at
        timestamp updated_at
    }

    LOANS {
        uuid id PK
        uuid user_id FK "ON DELETE RESTRICT"
        int copy_id FK "nullable, ON DELETE RESTRICT"
        int digital_resource_id FK "nullable, ON DELETE RESTRICT"
        timestamp borrowed_at "NOT NULL"
        timestamp due_date "NOT NULL"
        timestamp returned_at "nullable"
        loan_status status "ACTIVE RETURNED OVERDUE"
    }
```

## Contraintes et règles de gestion

| Règle | Détail |
|---|---|
| CK `ck_loan_exactly_one_target` | Un prêt cible **exactement un** exemplaire **ou** une ressource numérique (jamais les deux, jamais aucun) |
| Suppression en cascade | Supprimer un `book` supprime ses `copies` et `digital_resources` |
| Card number | Généré par rôle : `ETU-2026-00451`, préfixes ETU/ENS/PER/BIB/ADM |
| QR code exemplaire | Identifiant opaque `BK-XXXXXXXX` collé physiquement sur chaque copie |
| Catégorisation | Pas de table Catégorie/Auteur/Éditeur : colonnes texte sur `books` + classification Dewey |
| Horodatage | Toutes les tables portent `created_at` / `updated_at` (TimestampMixin) |
