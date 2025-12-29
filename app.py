import json
import os
import random
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "data.db")
DEFAULT_ELO = 1500.0
ELO_K = 24.0
POOL_SIZE = 200
FOCUS_SIZE = 30


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            list_id TEXT NOT NULL,
            type TEXT NOT NULL,
            payload TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(list_id) REFERENCES lists(id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ratings (
            item_id TEXT PRIMARY KEY,
            elo REAL NOT NULL,
            games INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(item_id) REFERENCES items(id)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pairs (
            id TEXT PRIMARY KEY,
            list_id TEXT NOT NULL,
            left_item_id TEXT NOT NULL,
            right_item_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            answered INTEGER NOT NULL DEFAULT 0,
            winner_item_id TEXT,
            FOREIGN KEY(list_id) REFERENCES lists(id),
            FOREIGN KEY(left_item_id) REFERENCES items(id),
            FOREIGN KEY(right_item_id) REFERENCES items(id)
        );
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_list_active ON items(list_id, active);"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ratings_item ON ratings(item_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pairs_list ON pairs(list_id);")
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Subjective Ranking Engine", lifespan=lifespan)

# Allow local dev without CORS hassle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ListCreate(BaseModel):
    name: str


class ListOut(BaseModel):
    list_id: str = Field(alias="id")
    name: str
    created_at: str
    model_config = {"populate_by_name": True}


class ItemCreate(BaseModel):
    type: str
    payload: Any


class ItemUpdate(BaseModel):
    type: Optional[str] = None
    payload: Optional[Any] = None
    active: Optional[bool] = None


class ItemOut(BaseModel):
    item_id: str = Field(alias="id")
    type: str
    payload: Any
    active: bool
    model_config = {"populate_by_name": True}


class PairOut(BaseModel):
    pair_id: str = Field(alias="id")
    left: ItemOut
    right: ItemOut
    model_config = {"populate_by_name": True}


class VoteIn(BaseModel):
    pair_id: str
    winner: str


class StatusOut(BaseModel):
    list_id: str
    stability: float
    sorted_items: list[ItemOut]


@app.get("/health")
def health() -> dict:
    return {"ok": True}


def serialize_payload(payload: Any) -> str:
    return json.dumps(payload)


def deserialize_payload(item_type: str, payload_text: str) -> Any:
    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError:
        data = payload_text
    if item_type == "number":
        if isinstance(data, (int, float)):
            return data
        try:
            return float(data)
        except Exception:
            return data
    if item_type == "json":
        return data
    return str(data)


def elo_prob(a: float, b: float) -> float:
    return 1.0 / (1 + 10 ** (-(a - b) / 400))


@app.post("/lists", response_model=ListOut)
def create_list(payload: ListCreate):
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    list_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO lists(id, name, created_at) VALUES (?, ?, ?)",
        (list_id, payload.name, now),
    )
    conn.commit()
    conn.close()
    return {"id": list_id, "name": payload.name, "created_at": now}


@app.get("/lists", response_model=list[ListOut])
def list_lists():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, created_at FROM lists ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"id": r["id"], "name": r["name"], "created_at": r["created_at"]} for r in rows
    ]


@app.get("/lists/{list_id}", response_model=ListOut)
def get_list(list_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, created_at FROM lists WHERE id = ?", (list_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="List not found")
    return {"id": row["id"], "name": row["name"], "created_at": row["created_at"]}


def ensure_list_exists(list_id: str, conn: sqlite3.Connection) -> None:
    found = conn.execute("SELECT 1 FROM lists WHERE id = ?", (list_id,)).fetchone()
    if not found:
        raise HTTPException(status_code=404, detail="List not found")


@app.post("/lists/{list_id}/items", response_model=ItemOut)
def create_item(list_id: str, payload: ItemCreate):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    payload_text = serialize_payload(payload.payload)
    conn.execute(
        "INSERT INTO items(id, list_id, type, payload, active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
        (item_id, list_id, payload.type, payload_text, now, now),
    )
    conn.execute(
        "INSERT INTO ratings(item_id, elo, games, updated_at) VALUES (?, ?, 0, ?)",
        (item_id, DEFAULT_ELO, now),
    )
    conn.commit()
    conn.close()
    return {
        "id": item_id,
        "type": payload.type,
        "payload": payload.payload,
        "active": True,
    }


@app.get("/lists/{list_id}/items", response_model=list[ItemOut])
def list_items(list_id: str, include_inactive: bool = Query(False)):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    rows = conn.execute(
        "SELECT id, type, payload, active FROM items WHERE list_id = ? AND (? OR active = 1) ORDER BY created_at",
        (list_id, 1 if include_inactive else 0),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append(
            {
                "id": r["id"],
                "type": r["type"],
                "payload": deserialize_payload(r["type"], r["payload"]),
                "active": bool(r["active"]),
            }
        )
    return result


@app.patch("/lists/{list_id}/items/{item_id}", response_model=ItemOut)
def update_item(list_id: str, item_id: str, payload: ItemUpdate):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    row = conn.execute(
        "SELECT id, type, payload, active FROM items WHERE id = ? AND list_id = ?",
        (item_id, list_id),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    new_type = payload.type or row["type"]
    new_payload_text = row["payload"]
    if payload.payload is not None:
        new_payload_text = serialize_payload(payload.payload)
    new_active = payload.active if payload.active is not None else bool(row["active"])
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "UPDATE items SET type = ?, payload = ?, active = ?, updated_at = ? WHERE id = ?",
        (new_type, new_payload_text, 1 if new_active else 0, now, item_id),
    )
    conn.commit()
    conn.close()
    return {
        "id": item_id,
        "type": new_type,
        "payload": deserialize_payload(new_type, new_payload_text),
        "active": new_active,
    }


@app.delete("/lists/{list_id}/items/{item_id}")
def delete_item(list_id: str, item_id: str):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    cur = conn.cursor()
    cur.execute(
        "UPDATE items SET active = 0, updated_at = ? WHERE id = ? AND list_id = ?",
        (datetime.now(timezone.utc).isoformat(), item_id, list_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


def fetch_active_pool(conn: sqlite3.Connection, list_id: str) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT i.id, i.type, i.payload, i.active, r.elo, r.games
        FROM items i
        JOIN ratings r ON r.item_id = i.id
        WHERE i.list_id = ? AND i.active = 1
        ORDER BY r.games ASC
        LIMIT ?
        """,
        (list_id, POOL_SIZE),
    ).fetchall()
    return rows


def select_pair(
    conn: sqlite3.Connection, list_id: str
) -> tuple[sqlite3.Row, sqlite3.Row]:
    pool = fetch_active_pool(conn, list_id)
    if len(pool) < 2:
        raise HTTPException(status_code=400, detail="Not enough active items")
    focus_candidates = pool[: min(len(pool), FOCUS_SIZE)]
    focus = random.choice(focus_candidates)
    opponents = [row for row in pool if row["id"] != focus["id"]]
    opponents.sort(key=lambda row: abs(row["elo"] - focus["elo"]))
    opponent = opponents[0]
    return focus, opponent


def row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "type": row["type"],
        "payload": deserialize_payload(row["type"], row["payload"]),
        "active": bool(row["active"]),
    }


@app.get("/lists/{list_id}/pair", response_model=PairOut)
def get_pair(list_id: str):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    left_row, right_row = select_pair(conn, list_id)
    pair_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO pairs(id, list_id, left_item_id, right_item_id, created_at, answered) VALUES (?, ?, ?, ?, ?, 0)",
        (pair_id, list_id, left_row["id"], right_row["id"], now),
    )
    conn.commit()
    conn.close()
    return {
        "id": pair_id,
        "left": row_to_item(left_row),
        "right": row_to_item(right_row),
    }


def fetch_pair(
    conn: sqlite3.Connection, pair_id: str, list_id: str
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM pairs WHERE id = ? AND list_id = ?",
        (pair_id, list_id),
    ).fetchone()


def fetch_item(conn: sqlite3.Connection, item_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT i.id, i.type, i.payload, i.active, r.elo, r.games FROM items i JOIN ratings r ON r.item_id = i.id WHERE i.id = ?",
        (item_id,),
    ).fetchone()


def update_rating(
    conn: sqlite3.Connection, item_id: str, elo: float, games: int
) -> None:
    conn.execute(
        "UPDATE ratings SET elo = ?, games = ?, updated_at = ? WHERE item_id = ?",
        (elo, games, datetime.now(timezone.utc).isoformat(), item_id),
    )


@app.post("/lists/{list_id}/vote")
def vote(list_id: str, payload: VoteIn):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    pair_row = fetch_pair(conn, payload.pair_id, list_id)
    if not pair_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pair not found")

    if pair_row["answered"]:
        conn.close()
        return {"ok": True, "ignored": "already_answered"}

    left = fetch_item(conn, pair_row["left_item_id"])
    right = fetch_item(conn, pair_row["right_item_id"])
    if not left or not right or not bool(left["active"]) or not bool(right["active"]):
        conn.execute(
            "UPDATE pairs SET answered = 1 WHERE id = ?",
            (payload.pair_id,),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "ignored": "item_inactive_or_missing"}

    winner_side = payload.winner.lower()
    if winner_side not in {"left", "right"}:
        conn.close()
        raise HTTPException(status_code=400, detail="winner must be 'left' or 'right'")

    elo_left = float(left["elo"])
    elo_right = float(right["elo"])
    p_left = elo_prob(elo_left, elo_right)

    if winner_side == "left":
        score_left = 1.0
        score_right = 0.0
        winner_id = left["id"]
    else:
        score_left = 0.0
        score_right = 1.0
        winner_id = right["id"]

    new_elo_left = elo_left + ELO_K * (score_left - p_left)
    new_elo_right = elo_right + ELO_K * (score_right - (1 - p_left))

    update_rating(conn, left["id"], new_elo_left, int(left["games"]) + 1)
    update_rating(conn, right["id"], new_elo_right, int(right["games"]) + 1)

    conn.execute(
        "UPDATE pairs SET answered = 1, winner_item_id = ? WHERE id = ?",
        (winner_id, payload.pair_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/lists/{list_id}/status", response_model=StatusOut)
def status(list_id: str):
    conn = get_conn()
    ensure_list_exists(list_id, conn)
    rows = conn.execute(
        """
        SELECT i.id, i.type, i.payload, i.active, r.elo, r.games
        FROM items i
        JOIN ratings r ON r.item_id = i.id
        WHERE i.list_id = ? AND i.active = 1
        ORDER BY r.elo DESC
        """,
        (list_id,),
    ).fetchall()
    conn.close()
    items = [row_to_item(r) for r in rows]
    stability = 1.0
    if len(rows) >= 2:
        probs = []
        for idx in range(len(rows) - 1):
            probs.append(elo_prob(rows[idx]["elo"], rows[idx + 1]["elo"]))
        stability = float(sum(probs) / len(probs)) if probs else 1.0
    return {"list_id": list_id, "stability": stability, "sorted_items": items}


# Serve static assets
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/static/index.html")
