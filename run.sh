#!/bin/bash
# Script de démarrage rapide pour le Subjective Ranking Engine

set -e

echo "🚀 Subjective Ranking Engine"
echo "=============================="

# Vérifier si venv existe
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer venv
source venv/bin/activate

# Installer les dépendances
echo "📦 Installation des dépendances..."
pip install -q -r requirements.txt

# Démarrer le serveur
echo "✅ Démarrage du serveur sur http://localhost:8000"
echo ""
echo "Pages disponibles :"
echo "  - http://localhost:8000          (Accueil)"
echo "  - http://localhost:8000/static/admin.html  (Administration)"
echo "  - http://localhost:8000/static/vote.html   (Vote)"
echo "  - http://localhost:8000/static/status.html (Status)"
echo "  - http://localhost:8000/docs     (Documentation API)"
echo ""
uvicorn app:app --reload --host 0.0.0.0 --port 8000
