#!/usr/bin/env python3
"""
Script de démonstration du Subjective Ranking Engine
Crée une liste, ajoute des items, effectue quelques votes et affiche le status.
"""

import httpx
import json
import time

BASE_URL = "http://localhost:8000"


def main():
    print("🎬 Démonstration Subjective Ranking Engine\n")

    # Créer une liste
    print("1️⃣  Création d'une liste de films...")
    response = httpx.post(f"{BASE_URL}/lists", json={"name": "Meilleurs Films Sci-Fi"})
    list_data = response.json()
    list_id = list_data["id"]
    print(f"   ✅ Liste créée : {list_id}\n")

    # Ajouter des films
    print("2️⃣  Ajout de 5 films...")
    films = ["Inception", "The Matrix", "Interstellar", "Blade Runner 2049", "Arrival"]

    for film in films:
        httpx.post(
            f"{BASE_URL}/lists/{list_id}/items", json={"type": "text", "payload": film}
        )
    print(f"   ✅ {len(films)} films ajoutés\n")

    # Effectuer des votes
    print("3️⃣  Simulation de 10 votes...")
    for i in range(10):
        pair_resp = httpx.get(f"{BASE_URL}/lists/{list_id}/pair")
        pair = pair_resp.json()

        left = pair["left"]["payload"]
        right = pair["right"]["payload"]

        # Simuler un choix (ici, juste alphabétique pour la démo)
        winner = "left" if left < right else "right"

        httpx.post(
            f"{BASE_URL}/lists/{list_id}/vote",
            json={"pair_id": pair["id"], "winner": winner},
        )
        print(
            f"   Vote {i + 1}/10 : {left} vs {right} → gagnant: {pair[winner]['payload']}"
        )

    print()

    # Afficher le status
    print("4️⃣  Status final du classement...")
    status_resp = httpx.get(f"{BASE_URL}/lists/{list_id}/status")
    status = status_resp.json()

    print(f"   📊 Stabilité : {status['stability']:.3f}")
    print(f"   🏆 Classement :\n")

    for idx, item in enumerate(status["sorted_items"], 1):
        print(f"      {idx}. {item['payload']}")

    print(
        f"\n✨ Démo terminée ! Consultez http://localhost:8000/static/status.html pour voir les résultats."
    )


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("❌ Erreur : Le serveur n'est pas démarré.")
        print("   Lancez d'abord : ./run.sh ou make dev")
    except Exception as e:
        print(f"❌ Erreur : {e}")
