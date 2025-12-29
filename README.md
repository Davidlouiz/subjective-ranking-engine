# Subjective Ranking Engine

Service FastAPI pour classer des éléments par votes binaires (pairwise) avec stockage SQLite par défaut et trois pages statiques pour l'admin, le vote et le statut.

## ✨ Fonctionnalités

- **Algorithme Elo** pour le classement subjectif avec convergence rapide
- **Sélection intelligente de paires** : favorise les items peu comparés et Elo proches
- **Soft delete** : désactivation des items sans perte d'historique
- **Stabilité** : métrique 0..1 calculée sur les probabilités Elo adjacentes
- **3 interfaces** : admin, vote, status
- **API REST** complète avec documentation OpenAPI

## 🚀 Démarrage rapide

### Option 1 : Script shell
```bash
./run.sh
```

### Option 2 : Makefile
```bash
make install  # Première fois
make dev      # Lancer en mode dev
make test     # Exécuter les tests
```

### Option 3 : Manuel
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Puis ouvrir http://localhost:8000

## 📱 Pages disponibles

- **/** — Page d'accueil avec navigation
- **/static/admin.html** — Gestion listes et items (CRUD, soft delete/réactivation)
- **/static/vote.html** — Interface de vote sur paires
- **/static/status.html** — Stabilité + classement trié (auto-refresh optionnel)
- **/docs** — Documentation API interactive (Swagger)
- **/health** — Health check

## 🔧 API (résumé)

### Listes
- `POST /lists` — créer une liste `{"name": "..."}`
- `GET /lists` — lister toutes les listes
- `GET /lists/{list_id}` — détails d'une liste

### Items
- `POST /lists/{list_id}/items` — créer un item `{"type": "text|number|image|json", "payload": ...}`
- `GET /lists/{list_id}/items?include_inactive=bool` — lister les items
- `PATCH /lists/{list_id}/items/{item_id}` — modifier type/payload/active
- `DELETE /lists/{list_id}/items/{item_id}` — soft delete (active=false)

### Vote
- `GET /lists/{list_id}/pair` — obtenir une paire `{pair_id, left, right}`
- `POST /lists/{list_id}/vote` — voter `{"pair_id": "...", "winner": "left|right"}`
  - Ignore automatiquement si pair déjà répondue ou item inactif

### Status
- `GET /lists/{list_id}/status` — `{stability: 0..1, sorted_items: [...]}`

## 🧪 Tests

```bash
make test
# ou
pytest -v
```

Couvre :
- Calcul Elo et probabilités
- Sélection de paires (2 items distincts actifs)
- Flow complet : création liste → ajout items → pair → vote → status
- Soft delete puis vote sur ancienne paire → ignoré sans crash

## 🎯 Algorithme (MVP)

### Sélection de paire
1. Pool : items actifs les moins joués (limite 200)
2. Focus : un item parmi les plus bas en `games` (limite 30)
3. Adversaire : minimise `|elo_focus - elo_opponent|` dans le pool

### Mise à jour Elo
- Classique avec K=24 par défaut
- `p(A gagne) = 1 / (1 + 10^(-(eloA - eloB)/400))`
- `eloA' = eloA + K * (score - p)`

### Stabilité
- Trier items actifs par Elo décroissant
- Pour chaque paire adjacente (i, i+1), calculer `p(i bat i+1)`
- Stabilité = moyenne de ces probabilités
- Interprétation : >0.9 = très stable, ~0.5 = instable

## 🗂️ Structure

```
.
├── app.py                 # API FastAPI + Elo + persistence SQLite
├── static/
│   ├── index.html         # Page d'accueil
│   ├── admin.html         # Interface admin
│   ├── vote.html          # Interface vote
│   └── status.html        # Interface status
├── tests/
│   └── test_app.py        # Tests unitaires + intégration
├── requirements.txt
├── Makefile
├── run.sh                 # Script de lancement rapide
└── README.md
```

## 📊 Configuration

- **DB_PATH** : chemin SQLite (défaut: `data.db`)
- **ELO_K** : facteur K Elo (défaut: 24)
- **POOL_SIZE** : taille du pool de sélection (défaut: 200)
- **FOCUS_SIZE** : taille du sous-pool focus (défaut: 30)

## 📝 Notes

- Base SQLite par défaut `data.db` (configurable via env `DB_PATH`)
- Soft delete uniquement : items désactivés ne disparaissent jamais de la DB
- Pairs non réservées : plusieurs utilisateurs peuvent voter en parallèle
- Évolutivité testée jusqu'à 50k items (cible 100k)

## 🔮 Extensions futures (hors MVP)

- Modèles avancés : Bradley-Terry, TrueSkill
- Active learning pour sélection optimale de paires
- Auth légère + rate limiting
- Export CSV/JSON
- Analytics et historique détaillé
