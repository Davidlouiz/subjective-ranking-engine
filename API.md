# API Reference - Subjective Ranking Engine

Base URL: `http://localhost:8000`

## Health & Info

### `GET /health`
Health check endpoint.

**Response 200**
```json
{"ok": true}
```

---

## Lists

### `POST /lists`
Créer une nouvelle liste.

**Request Body**
```json
{
  "name": "Ma Liste"
}
```

**Response 200**
```json
{
  "id": "uuid-string",
  "name": "Ma Liste",
  "created_at": "2025-12-29T21:00:00+00:00"
}
```

### `GET /lists`
Lister toutes les listes.

**Response 200**
```json
[
  {
    "id": "uuid-string",
    "name": "Liste 1",
    "created_at": "2025-12-29T21:00:00+00:00"
  }
]
```

### `GET /lists/{list_id}`
Récupérer les détails d'une liste.

**Response 200**
```json
{
  "id": "uuid-string",
  "name": "Ma Liste",
  "created_at": "2025-12-29T21:00:00+00:00"
}
```

**Response 404**
```json
{"detail": "List not found"}
```

---

## Items

### `POST /lists/{list_id}/items`
Créer un nouvel item dans une liste.

**Request Body**
```json
{
  "type": "text",
  "payload": "Mon texte"
}
```

Types supportés:
- `text`: string simple
- `number`: nombre (int ou float)
- `image`: URL d'image (string)
- `json`: objet JSON arbitraire

**Response 200**
```json
{
  "id": "uuid-string",
  "type": "text",
  "payload": "Mon texte",
  "active": true
}
```

### `GET /lists/{list_id}/items`
Lister les items d'une liste.

**Query Parameters**
- `include_inactive` (bool, default: false): inclure les items désactivés

**Response 200**
```json
[
  {
    "id": "uuid-string",
    "type": "text",
    "payload": "Item 1",
    "active": true
  },
  {
    "id": "uuid-string-2",
    "type": "image",
    "payload": "https://example.com/img.jpg",
    "active": false
  }
]
```

### `PATCH /lists/{list_id}/items/{item_id}`
Modifier un item existant.

**Request Body** (tous les champs sont optionnels)
```json
{
  "type": "json",
  "payload": {"label": "Nouveau"},
  "active": true
}
```

**Response 200**
```json
{
  "id": "uuid-string",
  "type": "json",
  "payload": {"label": "Nouveau"},
  "active": true
}
```

### `DELETE /lists/{list_id}/items/{item_id}`
Désactiver un item (soft delete).

**Response 200**
```json
{"ok": true}
```

**Response 404**
```json
{"detail": "Item not found"}
```

---

## Voting

### `GET /lists/{list_id}/pair`
Récupérer une paire d'items à comparer.

**Response 200**
```json
{
  "id": "pair-uuid",
  "left": {
    "id": "item-uuid-1",
    "type": "text",
    "payload": "Option A",
    "active": true
  },
  "right": {
    "id": "item-uuid-2",
    "type": "text",
    "payload": "Option B",
    "active": true
  }
}
```

**Response 400**
```json
{"detail": "Not enough active items"}
```

### `POST /lists/{list_id}/vote`
Soumettre un vote sur une paire.

**Request Body**
```json
{
  "pair_id": "pair-uuid",
  "winner": "left"
}
```

`winner` doit être `"left"` ou `"right"`.

**Response 200** (vote enregistré)
```json
{"ok": true}
```

**Response 200** (vote ignoré - pair déjà répondue)
```json
{
  "ok": true,
  "ignored": "already_answered"
}
```

**Response 200** (vote ignoré - item inactif)
```json
{
  "ok": true,
  "ignored": "item_inactive_or_missing"
}
```

**Response 404**
```json
{"detail": "Pair not found"}
```

**Response 400**
```json
{"detail": "winner must be 'left' or 'right'"}
```

---

## Status

### `GET /lists/{list_id}/status`
Récupérer le classement et la stabilité d'une liste.

**Response 200**
```json
{
  "list_id": "uuid-string",
  "stability": 0.8732,
  "sorted_items": [
    {
      "id": "item-uuid-1",
      "type": "text",
      "payload": "Top item",
      "active": true
    },
    {
      "id": "item-uuid-2",
      "type": "text",
      "payload": "Second item",
      "active": true
    }
  ]
}
```

**Interprétation stabilité**:
- `< 0.6`: classement très instable, continuer les votes
- `0.6 - 0.8`: classement en cours de convergence
- `0.8 - 0.9`: classement assez stable
- `> 0.9`: classement très stable, consensus atteint

---

## Examples

### Workflow complet

```bash
# 1. Créer une liste
LIST_ID=$(curl -s -X POST http://localhost:8000/lists \
  -H "Content-Type: application/json" \
  -d '{"name":"Mes Films"}' | jq -r '.id')

# 2. Ajouter des items
curl -s -X POST http://localhost:8000/lists/$LIST_ID/items \
  -H "Content-Type: application/json" \
  -d '{"type":"text","payload":"Inception"}'

curl -s -X POST http://localhost:8000/lists/$LIST_ID/items \
  -H "Content-Type: application/json" \
  -d '{"type":"text","payload":"Matrix"}'

# 3. Obtenir une paire
PAIR=$(curl -s http://localhost:8000/lists/$LIST_ID/pair)
PAIR_ID=$(echo $PAIR | jq -r '.id')

# 4. Voter
curl -s -X POST http://localhost:8000/lists/$LIST_ID/vote \
  -H "Content-Type: application/json" \
  -d "{\"pair_id\":\"$PAIR_ID\",\"winner\":\"left\"}"

# 5. Voir le status
curl -s http://localhost:8000/lists/$LIST_ID/status | jq
```

### Réactiver un item désactivé

```bash
# Soft delete
curl -X DELETE http://localhost:8000/lists/$LIST_ID/items/$ITEM_ID

# Réactiver
curl -X PATCH http://localhost:8000/lists/$LIST_ID/items/$ITEM_ID \
  -H "Content-Type: application/json" \
  -d '{"active":true}'
```

### Types d'items

```bash
# Text
curl -X POST http://localhost:8000/lists/$LIST_ID/items \
  -H "Content-Type: application/json" \
  -d '{"type":"text","payload":"Simple text"}'

# Number
curl -X POST http://localhost:8000/lists/$LIST_ID/items \
  -H "Content-Type: application/json" \
  -d '{"type":"number","payload":42}'

# Image
curl -X POST http://localhost:8000/lists/$LIST_ID/items \
  -H "Content-Type: application/json" \
  -d '{"type":"image","payload":"https://picsum.photos/200"}'

# JSON
curl -X POST http://localhost:8000/lists/$LIST_ID/items \
  -H "Content-Type: application/json" \
  -d '{"type":"json","payload":{"name":"Complex","tags":["a","b"]}}'
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Resource not found |
| 422 | Validation Error (invalid JSON schema) |
| 500 | Internal Server Error |

---

## Rate Limiting

⚠️ Non implémenté dans le MVP. À ajouter en production.

Suggestion:
- 100 req/min par IP pour endpoints publics
- 10 req/min pour création de listes
- Illimité pour endpoints de lecture (GET)

---

## Documentation interactive

Consultez http://localhost:8000/docs pour explorer l'API de manière interactive via Swagger UI.
