import importlib
import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest

# Add parent dir to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))


def reload_app(db_path: str):
    os.environ["DB_PATH"] = db_path
    import app as app_module

    importlib.reload(app_module)
    app_module.init_db()
    return app_module


def test_elo_probability_and_update(tmp_path):
    app_module = reload_app(str(tmp_path / "elo.db"))
    p = app_module.elo_prob(1500, 1500)
    assert 0.49 < p < 0.51
    p_stronger = app_module.elo_prob(1600, 1400)
    assert p_stronger > 0.75


@pytest.mark.asyncio
async def test_pair_selection_and_vote_flow(tmp_path):
    db_path = tmp_path / "flow.db"
    app_module = reload_app(str(db_path))

    async with httpx.AsyncClient(app=app_module.app, base_url="http://test") as c:
        # Create list
        res = await c.post("/lists", json={"name": "Test"})
        assert res.status_code == 200
        list_id = res.json()["id"]

        # Add items
        for label in ("A", "B", "C"):
            res = await c.post(
                f"/lists/{list_id}/items", json={"type": "text", "payload": label}
            )
            assert res.status_code == 200

        # Get pair
        pair_res = await c.get(f"/lists/{list_id}/pair")
        assert pair_res.status_code == 200
        pair = pair_res.json()
        assert pair["left"]["id"] != pair["right"]["id"]

        # Vote
        vote_res = await c.post(
            f"/lists/{list_id}/vote", json={"pair_id": pair["id"], "winner": "left"}
        )
        assert vote_res.status_code == 200
        assert vote_res.json()["ok"] is True

        # Status
        status_res = await c.get(f"/lists/{list_id}/status")
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["list_id"] == list_id
        assert data["sorted_items"]


@pytest.mark.asyncio
async def test_soft_delete_then_vote_is_ignored(tmp_path):
    db_path = tmp_path / "softdelete.db"
    app_module = reload_app(str(db_path))

    async with httpx.AsyncClient(app=app_module.app, base_url="http://test") as c:
        res = await c.post("/lists", json={"name": "Ignore"})
        list_id = res.json()["id"]

        # Add two items
        res_left = await c.post(
            f"/lists/{list_id}/items", json={"type": "text", "payload": "Left"}
        )
        res_right = await c.post(
            f"/lists/{list_id}/items", json={"type": "text", "payload": "Right"}
        )
        left_id = res_left.json()["id"]
        right_id = res_right.json()["id"]

        pair = (await c.get(f"/lists/{list_id}/pair")).json()

        # Soft delete right item
        del_res = await c.delete(f"/lists/{list_id}/items/{right_id}")
        assert del_res.status_code == 200

        vote_res = await c.post(
            f"/lists/{list_id}/vote", json={"pair_id": pair["id"], "winner": "left"}
        )
        assert vote_res.status_code == 200
        assert vote_res.json().get("ignored") == "item_inactive_or_missing"
