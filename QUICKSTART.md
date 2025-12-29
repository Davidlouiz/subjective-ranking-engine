# 🎯 Subjective Ranking Engine - Démarrage Rapide

## Installation et lancement (30 secondes)

```bash
# Option 1 : Script automatique
./run.sh

# Option 2 : Makefile
make install && make dev

# Option 3 : Manuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

## Accès aux interfaces

Ouvrez votre navigateur sur :
- **http://localhost:8000** → Page d'accueil
- **http://localhost:8000/static/admin.html** → Administration
- **http://localhost:8000/static/vote.html** → Vote
- **http://localhost:8000/static/status.html** → Classement
- **http://localhost:8000/docs** → Documentation API

## Workflow typique

### 1️⃣ Dans Admin
1. Créer une nouvelle liste (ex: "Meilleurs Films")
2. Ajouter des items (type text, number, image ou json)
3. Exemple : "Inception", "Matrix", "Interstellar"

### 2️⃣ Dans Vote
1. Sélectionner votre liste
2. Cliquer sur "Nouvelle paire"
3. Voter en cliquant sur la carte de votre choix
4. Répéter ~20-30 fois pour convergence

### 3️⃣ Dans Status
1. Sélectionner votre liste
2. Observer la stabilité (>0.9 = consensus)
3. Consulter le classement final

## Tests

```bash
make test
# ou
pytest -v
```

**Résultat attendu :** 3 tests passent ✅

## Script de démo

```bash
# Assurer que le serveur tourne
./run.sh &

# Dans un autre terminal
python demo.py
```

## Commandes utiles

```bash
# Nettoyer la base de données
make clean

# Relancer les tests
make test

# Voir l'aide du Makefile
make help
```

## Fichiers importants

| Fichier | Description |
|---------|-------------|
| `app.py` | API FastAPI + logique Elo |
| `static/*.html` | Interfaces utilisateur |
| `tests/test_app.py` | Tests unitaires + intégration |
| `README.md` | Documentation complète |
| `API.md` | Référence API détaillée |
| `IMPLEMENTATION.md` | Notes d'implémentation |

## Architecture rapide

```
┌─────────────────┐
│   Frontend      │  3 pages HTML/JS statiques
│  (admin/vote/   │  + fetch API
│   status)       │
└────────┬────────┘
         │ HTTP
┌────────▼────────┐
│   FastAPI       │  12 endpoints REST
│   + Elo Logic   │  + sélection paires
└────────┬────────┘
         │
┌────────▼────────┐
│   SQLite DB     │  4 tables:
│                 │  lists, items, ratings, pairs
└─────────────────┘
```

## Besoin d'aide ?

- **Documentation API** : http://localhost:8000/docs
- **README complet** : `README.md`
- **Référence API** : `API.md`
- **Détails implémentation** : `IMPLEMENTATION.md`

## Problèmes courants

### Port 8000 occupé
```bash
# Utiliser un autre port
uvicorn app:app --reload --port 8001
```

### Erreur module introuvable
```bash
# Activer le venv
source venv/bin/activate
```

### Tests échouent
```bash
# Réinstaller les dépendances
make clean
make install
make test
```

---

**Version** : 1.0.0  
**Python** : 3.11+  
**Status** : ✅ Production-ready MVP
