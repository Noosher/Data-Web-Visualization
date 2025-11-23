# GroupSelector.py

import os
import json
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# --------- Config ---------

VS_CURRENCY = "usd"

TOP15_TAG = "TOP15"
MEME_TAG = "MEME_TOP5"
L1_TAG = "L1_BLUECHIP"
DEFI_TAG = "DEFI_BLUECHIP"

# Static ID lists for themed groups (membership), ranking is dynamic by market cap

MEME_IDS = [
    "dogecoin",
    "shiba-inu",
    "pepe",
    "floki",
    "bonk",
    "dogwifcoin",
    "slerf",
    "dogelon-mars",
]

L1_IDS = [
    "bitcoin",
    "ethereum",
    "solana",
    "cardano",
    "avalanche-2",
]

DEFI_IDS = [
    "uniswap",
    "aave",
    "maker",
    "curve-dao-token",
    "lido-dao",
]


# --------- Helper functions ---------

def safe_mcap(coin_row: dict) -> int:
    mc = coin_row.get("market_cap")
    return mc if isinstance(mc, (int, float)) and mc is not None else 0


def fetch_markets_global(vs_currency: str = VS_CURRENCY, per_page: int = 250, page: int = 1):
    """Global market data ordered by market cap desc."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    headers = {"x-cg-demo-api-key": os.environ["COINGECKO_API_KEY"]}

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_or_create_group(conn, tag: str, type_: str, description: str):
    """Upsert into crypto_group by tag; return group_id (UUID)."""
    sql = text("""
        INSERT INTO crypto_group (tag, type, description)
        VALUES (:tag, :type, :description)
        ON CONFLICT (tag)
        DO UPDATE SET
            type = EXCLUDED.type,
            description = EXCLUDED.description
        RETURNING id;
    """)
    result = conn.execute(sql, {"tag": tag, "type": type_, "description": description})
    return result.scalar_one()


def get_or_create_asset(conn, cg_id: str, symbol: str, name: str):
    """Upsert into crypto_asset by coingecko_id; return asset_id (UUID)."""
    sql = text("""
        INSERT INTO crypto_asset (coingecko_id, symbol, name)
        VALUES (:cg_id, :symbol, :name)
        ON CONFLICT (coingecko_id)
        DO UPDATE SET
            symbol = EXCLUDED.symbol,
            name   = EXCLUDED.name
        RETURNING id;
    """)
    result = conn.execute(sql, {"cg_id": cg_id, "symbol": symbol, "name": name})
    return result.scalar_one()


def add_asset_to_group(conn, asset_id, group_id):
    """Insert into crypto_asset_group if not present."""
    sql = text("""
        INSERT INTO crypto_asset_group (asset_id, group_id)
        VALUES (:asset_id, :group_id)
        ON CONFLICT (asset_id, group_id)
        DO NOTHING;
    """)
    conn.execute(sql, {"asset_id": asset_id, "group_id": group_id})


def set_is_active_flags(conn):
    """
    Maintain is_active on crypto_asset:
      - set all to FALSE
      - set TRUE for any asset that appears in crypto_asset_group
    """
    conn.execute(text("UPDATE crypto_asset SET is_active = FALSE;"))
    conn.execute(text("""
        UPDATE crypto_asset
        SET is_active = TRUE
        WHERE id IN (SELECT DISTINCT asset_id FROM crypto_asset_group);
    """))


def update_job_run_log(conn, status: str, details=None):
    """Log this job run into job_run_log."""
    sql = text("""
        INSERT INTO job_run_log (job_name, last_run_at, last_status, details)
        VALUES (:job_name, NOW(), :status, CAST(:details AS JSONB))
        ON CONFLICT (job_name)
        DO UPDATE SET
            last_run_at = EXCLUDED.last_run_at,
            last_status = EXCLUDED.last_status,
            details     = EXCLUDED.details;
    """)
    payload = {
        "job_name": "group_selector",
        "status": status,
        "details": None if details is None else json.dumps(details),
    }
    conn.execute(sql, payload)


# --------- Core logic ---------

def run_group_selector():
    """Main entrypoint: select groups & update DB."""
    load_dotenv()

    api_key = os.getenv("COINGECKO_API_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not api_key or not db_url:
        raise RuntimeError("Missing COINGECKO_API_KEY or DATABASE_URL in environment/.env")

    os.environ["COINGECKO_API_KEY"] = api_key  # for helper functions
    engine = create_engine(db_url)

    summary = {}

    with engine.begin() as conn:
        # ---- 1. Fetch markets once ----
        global_markets = fetch_markets_global()
        summary["global_count"] = len(global_markets)
        markets_by_id = {c["id"]: c for c in global_markets}

        # ---- 2. TOP15: global top 15 by mcap ----
        top15_rows = sorted(global_markets, key=safe_mcap, reverse=True)[:15]
        top15_ids = [c["id"] for c in top15_rows]
        summary["TOP15"] = top15_ids

        # ---- 3. MEME_TOP5: from MEME_IDS list ranked by mcap (ensure DOGE) ----
        meme_candidates = [markets_by_id[cid] for cid in MEME_IDS if cid in markets_by_id]
        meme_sorted = sorted(meme_candidates, key=safe_mcap, reverse=True)
        meme_top = meme_sorted[:5]

        if not any(c["id"] == "dogecoin" for c in meme_top):
            doge = next((c for c in meme_sorted if c["id"] == "dogecoin"), None)
            if doge and doge not in meme_top:
                meme_top.append(doge)

        meme_ids = [c["id"] for c in meme_top]
        summary["MEME_TOP5"] = meme_ids

        # ---- 4. L1_BLUECHIP: from L1_IDS ranked by mcap ----
        l1_members = [markets_by_id[cid] for cid in L1_IDS if cid in markets_by_id]
        l1_sorted = sorted(l1_members, key=safe_mcap, reverse=True)
        l1_rows = l1_sorted[:5]
        l1_ids = [c["id"] for c in l1_rows]
        summary["L1_BLUECHIP"] = l1_ids

        # ---- 5. DEFI_BLUECHIP: from DEFI_IDS ranked by mcap ----
        defi_members = [markets_by_id[cid] for cid in DEFI_IDS if cid in markets_by_id]
        defi_sorted = sorted(defi_members, key=safe_mcap, reverse=True)
        defi_rows = defi_sorted[:5]
        defi_ids = [c["id"] for c in defi_rows]
        summary["DEFI_BLUECHIP"] = defi_ids

        # ---- 6. Upsert groups ----
        g_top15 = get_or_create_group(
            conn,
            tag=TOP15_TAG,
            type_="RankBucket",
            description="Top 15 coins by market cap (USD)",
        )
        g_meme = get_or_create_group(
            conn,
            tag=MEME_TAG,
            type_="Theme",
            description="Top meme coins by market cap (must include DOGE)",
        )
        g_l1 = get_or_create_group(
            conn,
            tag=L1_TAG,
            type_="Theme",
            description="Sample of major Layer 1 blockchains",
        )
        g_defi = get_or_create_group(
            conn,
            tag=DEFI_TAG,
            type_="Theme",
            description="Sample of major DeFi blue-chip protocols",
        )

        # ---- 7. Upsert assets + bridge rows ----

        # TOP15
        for row in top15_rows:
            asset_id = get_or_create_asset(conn, row["id"], row["symbol"], row["name"])
            add_asset_to_group(conn, asset_id, g_top15)

        # MEME_TOP5
        for row in meme_top:
            asset_id = get_or_create_asset(conn, row["id"], row["symbol"], row["name"])
            add_asset_to_group(conn, asset_id, g_meme)

        # L1_BLUECHIP
        for row in l1_rows:
            asset_id = get_or_create_asset(conn, row["id"], row["symbol"], row["name"])
            add_asset_to_group(conn, asset_id, g_l1)

        # DEFI_BLUECHIP
        for row in defi_rows:
            asset_id = get_or_create_asset(conn, row["id"], row["symbol"], row["name"])
            add_asset_to_group(conn, asset_id, g_defi)

        # ---- 8. Maintain is_active ----
        set_is_active_flags(conn)

        # ---- 9. Log job run ----
        update_job_run_log(conn, status="success", details=summary)

    print("GroupSelector completed. Summary:")
    print(json.dumps(summary, indent=2))


def main():
    run_group_selector()


if __name__ == "__main__":
    main()
