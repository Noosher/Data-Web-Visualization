# GroupSelector.py

import os
import json

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from config import (
    VS_CURRENCY,
    TOP15_TAG,
    MEME_TAG,
    L1_TAG,
    DEFI_TAG,
    MEME_CATEGORY,
    L1_CATEGORY,
    DEFI_CATEGORY,
    GROUP_SELECTOR_JOB_NAME,
)

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


def fetch_markets_by_category(
    category: str,
    vs_currency: str = VS_CURRENCY,
    per_page: int = 50,
    page: int = 1,
):
    """
    Fetch market data for a given CoinGecko category,
    ordered by market cap desc.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "24h",
        "category": category,
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
        "job_name": GROUP_SELECTOR_JOB_NAME,
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

    os.environ["COINGECKO_API_KEY"] = api_key
    engine = create_engine(db_url)

    summary = {}

    with engine.begin() as conn:
        # ---- 1. Fetch global markets once ----
        global_markets = fetch_markets_global()
        summary["global_count"] = len(global_markets)
        markets_by_id = {c["id"]: c for c in global_markets}

        # ---- 2. TOP15: global top 15 by mcap ----
        top15_rows = sorted(global_markets, key=safe_mcap, reverse=True)[:15]
        top15_ids = [c["id"] for c in top15_rows]
        summary["TOP15"] = top15_ids

        # ---- 3. MEME_TOP5 (dynamic category, enforce DOGE rule) ----
        meme_candidates = fetch_markets_by_category(MEME_CATEGORY)
        meme_candidates = sorted(meme_candidates, key=safe_mcap, reverse=True)

        base_top = meme_candidates[:5]  # top 5 by mcap
        base_ids = [c["id"] for c in base_top]

        if "dogecoin" in base_ids:
            # DOGE is already in top 5 -> exactly 5 members
            meme_rows = base_top
        else:
            # Need to append DOGE so group has 6 if possible
            doge_row = next((c for c in meme_candidates if c["id"] == "dogecoin"), None)
            if doge_row is None:
                # Fallback: try global markets for DOGE
                doge_row = markets_by_id.get("dogecoin")
            meme_rows = list(base_top)
            if doge_row is not None and doge_row["id"] not in base_ids:
                meme_rows.append(doge_row)

        meme_ids = [c["id"] for c in meme_rows]
        summary["MEME_TOP5"] = meme_ids  # may have 5 or 6 entries

        # ---- 4. L1_BLUECHIP: from L1 category ranked by mcap ----
        l1_candidates = fetch_markets_by_category(L1_CATEGORY)
        l1_candidates = sorted(l1_candidates, key=safe_mcap, reverse=True)
        l1_rows = l1_candidates[:5]
        l1_ids = [c["id"] for c in l1_rows]
        summary["L1_BLUECHIP"] = l1_ids

        # ---- 5. DEFI_BLUECHIP: from DeFi category ranked by mcap ----
        defi_candidates = fetch_markets_by_category(DEFI_CATEGORY)
        defi_candidates = sorted(defi_candidates, key=safe_mcap, reverse=True)
        defi_rows = defi_candidates[:5]
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
            description="Top meme coins by market cap (must include DOGE; 5 or 6 members)",
        )
        g_l1 = get_or_create_group(
            conn,
            tag=L1_TAG,
            type_="Theme",
            description="Sample of major Layer 1 blockchains (top by market cap in category)",
        )
        g_defi = get_or_create_group(
            conn,
            tag=DEFI_TAG,
            type_="Theme",
            description="Sample of major DeFi blue-chip protocols (top by market cap in category)",
        )

        # ---- 6b. Clear existing memberships for these groups (so re-runs are clean) ----
        conn.execute(text("""
            DELETE FROM crypto_asset_group
            WHERE group_id IN (:g_top15, :g_meme, :g_l1, :g_defi);
        """), {
            "g_top15": g_top15,
            "g_meme": g_meme,
            "g_l1": g_l1,
            "g_defi": g_defi,
        })

        # ---- 7. Upsert assets + bridge rows ----

        # TOP15
        for row in top15_rows:
            asset_id = get_or_create_asset(conn, row["id"], row["symbol"], row["name"])
            add_asset_to_group(conn, asset_id, g_top15)

        # MEME_TOP5 (+DOGE if needed)
        for row in meme_rows:
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
