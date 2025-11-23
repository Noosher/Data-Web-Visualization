# bulk_import.py

import os
import json
from datetime import datetime, timezone
from collections import OrderedDict

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from config import (
    VS_CURRENCY,
    BULK_DAYS_BACK,
    TABLE_PRICE_DAILY,
    TABLE_PRICE_HOURLY,
    BULK_IMPORT_JOB_NAME,
    ENABLE_HOURLY,  # <- add this in config.py
)

# CoinGecko demo behaviour (simplified summary):
#  - Very recent range  -> sub-hourly / hourly
#  - Medium range       -> hourly
#  - Longer range       -> daily bars
# We do NOT send `interval`; CoinGecko chooses granularity automatically.
# For both daily and "hourly" tables we allow requests up to BULK_DAYS_BACK
# (e.g. 1 year). Older parts of that window may come back as daily data, but
# you still get a continuous 1-year time series.

BASE_URL = "https://api.coingecko.com/api/v3"


# -------------------------
# HTTP / API helpers
# -------------------------

def _get_api_key() -> str:
    key = os.environ.get("COINGECKO_API_KEY")
    if not key:
        raise RuntimeError("COINGECKO_API_KEY not set in environment")
    return key


def fetch_market_chart_raw(
    coin_id: str,
    vs_currency: str,
    days: int,
) -> dict:
    api_key = _get_api_key()

    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": vs_currency,
        "days": days,
        "precision": "full",
    }
    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": api_key,
    }

    resp = requests.get(url, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _parse_market_chart_to_rows(payload: dict):
    prices = payload.get("prices", []) or []
    market_caps = payload.get("market_caps", []) or []
    volumes = payload.get("total_volumes", []) or []

    rows = []
    for (ts_p, price), (ts_mc, mc), (ts_v, vol) in zip(prices, market_caps, volumes):
        ts = datetime.fromtimestamp(ts_p / 1000.0, tz=timezone.utc)
        rows.append(
            {
                "observed_at": ts,
                "price": float(price),
                "market_cap_usd": float(mc) if mc is not None else None,
                "volume_24h_usd": float(vol) if vol is not None else None,
            }
        )

    rows.sort(key=lambda r: r["observed_at"])
    return rows


def fetch_daily_series(coin_id: str, days: int):
    days = max(1, min(days, BULK_DAYS_BACK))
    payload = fetch_market_chart_raw(coin_id, VS_CURRENCY, days)
    rows = _parse_market_chart_to_rows(payload)

    by_date: OrderedDict[datetime.date, dict] = OrderedDict()
    for r in rows:
        d = r["observed_at"].date()
        by_date[d] = r  # last one wins

    daily_rows = list(by_date.values())
    daily_rows.sort(key=lambda r: r["observed_at"])
    return daily_rows


def fetch_hourly_series(coin_id: str, days: int):
    days = max(1, min(days, BULK_DAYS_BACK))
    payload = fetch_market_chart_raw(coin_id, VS_CURRENCY, days)
    rows = _parse_market_chart_to_rows(payload)
    return rows


# -------------------------
# DB helpers
# -------------------------

def get_active_assets(conn):
    sql = text("""
        SELECT id, coingecko_id, symbol, name, last_active
        FROM crypto_asset
        WHERE is_active = TRUE;
    """)
    result = conn.execute(sql)
    return [dict(row._mapping) for row in result.fetchall()]


def compute_days_to_pull(last_active):
    """
    Rules:
      - last_active is NULL         -> full BULK_DAYS_BACK
      - last_active older than N    -> full BULK_DAYS_BACK
      - last_active within N days   -> delta from last_active to now
                                       approx (now - last_active).days + 2
    """
    now = datetime.now(timezone.utc)

    if last_active is None:
        return BULK_DAYS_BACK

    delta_days = (now - last_active).days

    if delta_days >= BULK_DAYS_BACK:
        return BULK_DAYS_BACK

    return min(BULK_DAYS_BACK, max(1, delta_days + 2))


def bulk_insert_prices_and_update_last_active(conn, asset_id, coin_id: str, days_to_pull: int):

    # ---- Fetch daily (always) ----
    daily_rows = fetch_daily_series(
        coin_id=coin_id,
        days=days_to_pull,
    )

    # ---- Fetch hourly (optional) ----
    hourly_rows = []
    hourly_error = None
    if ENABLE_HOURLY:
        try:
            hourly_rows = fetch_hourly_series(
                coin_id=coin_id,
                days=days_to_pull,
            )
        except Exception as ex:  # don't kill the whole asset on hourly failure
            hourly_error = str(ex)
            hourly_rows = []

    # Insert daily
    if daily_rows:
        insert_daily_sql = text(f"""
            INSERT INTO {TABLE_PRICE_DAILY} (
                asset_id,
                observed_at,
                currency_code,
                price,
                market_cap_usd,
                volume_24h_usd
            )
            VALUES (
                :asset_id,
                :observed_at,
                :currency_code,
                :price,
                :market_cap_usd,
                :volume_24h_usd
            )
            ON CONFLICT (asset_id, observed_at, currency_code)
            DO NOTHING;
        """)
        conn.execute(
            insert_daily_sql,
            [
                {
                    "asset_id": asset_id,
                    "observed_at": r["observed_at"],
                    "currency_code": VS_CURRENCY.upper(),
                    "price": r["price"],
                    "market_cap_usd": r["market_cap_usd"],
                    "volume_24h_usd": r["volume_24h_usd"],
                }
                for r in daily_rows
            ],
        )

    # Insert hourly
    if ENABLE_HOURLY and hourly_rows:
        insert_hourly_sql = text(f"""
            INSERT INTO {TABLE_PRICE_HOURLY} (
                asset_id,
                observed_at,
                currency_code,
                price,
                market_cap_usd,
                volume_24h_usd
            )
            VALUES (
                :asset_id,
                :observed_at,
                :currency_code,
                :price,
                :market_cap_usd,
                :volume_24h_usd
            )
            ON CONFLICT (asset_id, observed_at, currency_code)
            DO NOTHING;
        """)
        conn.execute(
            insert_hourly_sql,
            [
                {
                    "asset_id": asset_id,
                    "observed_at": r["observed_at"],
                    "currency_code": VS_CURRENCY.upper(),
                    "price": r["price"],
                    "market_cap_usd": r["market_cap_usd"],
                    "volume_24h_usd": r["volume_24h_usd"],
                }
                for r in hourly_rows
            ],
        )

    # Determine max observed_at across both grains
    last_ts_candidates = []
    if daily_rows:
        last_ts_candidates.append(daily_rows[-1]["observed_at"])
    if hourly_rows:
        last_ts_candidates.append(hourly_rows[-1]["observed_at"])

    if last_ts_candidates:
        last_ts = max(last_ts_candidates)
        update_sql = text("""
            UPDATE crypto_asset
            SET last_active = :last_ts
            WHERE id = :asset_id
              AND (last_active IS NULL OR last_active < :last_ts);
        """)
        conn.execute(update_sql, {"asset_id": asset_id, "last_ts": last_ts})

    return {
        "daily_rows": len(daily_rows),
        "hourly_rows": len(hourly_rows),
        "hourly_error": hourly_error,
    }


def update_job_run_log(conn, status: str, details=None):
    """
    Log this job run into job_run_log.
    """
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
        "job_name": BULK_IMPORT_JOB_NAME,
        "status": status,
        "details": None if details is None else json.dumps(details),
    }
    conn.execute(sql, payload)


# -------------------------
# Core logic
# -------------------------

def run_bulk_import():
    load_dotenv()

    api_key = os.getenv("COINGECKO_API_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not api_key or not db_url:
        raise RuntimeError("Missing COINGECKO_API_KEY or DATABASE_URL in environment/.env")

    os.environ["COINGECKO_API_KEY"] = api_key

    engine = create_engine(db_url)

    # Step 1: find which assets to consider
    with engine.begin() as conn:
        assets = get_active_assets(conn)

    if not assets:
        with engine.begin() as conn:
            update_job_run_log(conn, status="success", details={"asset_count": 0})
        print("BulkImport: no active assets found.")
        return

    summary = {
        "asset_count": len(assets),
        "per_asset_rows": {},
        "errors": {},
    }

    # Step 2: pull + insert per asset
    for asset in assets:
        asset_id = asset["id"]
        cg_id = asset["coingecko_id"]
        symbol = asset["symbol"]
        name = asset["name"]
        last_active = asset["last_active"]

        days_to_pull = compute_days_to_pull(last_active)

        print(f"\n=== Bulk importing {name} ({symbol}) [{cg_id}] for ~{days_to_pull} days ===")

        try:
            with engine.begin() as conn:
                counts = bulk_insert_prices_and_update_last_active(
                    conn,
                    asset_id=asset_id,
                    coin_id=cg_id,
                    days_to_pull=days_to_pull,
                )

            summary["per_asset_rows"][cg_id] = {
                "daily": counts["daily_rows"],
                "hourly": counts["hourly_rows"],
                "days_requested": days_to_pull,
                "hourly_error": counts.get("hourly_error"),
            }

            print(
                f"Inserted {counts['daily_rows']} daily and "
                f"{counts['hourly_rows']} sub-daily points for {cg_id}"
            )
            if counts.get("hourly_error"):
                print(f"  (Hourly error for {cg_id}: {counts['hourly_error']})")

        except Exception as e:
            err_msg = str(e)
            summary["errors"][cg_id] = err_msg
            print(f"ERROR importing {cg_id}: {err_msg}")

    status = "success" if not summary["errors"] else "partial_success"

    # Step 3: update job_run_log
    with engine.begin() as conn:
        update_job_run_log(conn, status=status, details=summary)

    print("\nBulkImport completed. Summary:")
    print(json.dumps(summary, indent=2))


def main():
    run_bulk_import()


if __name__ == "__main__":
    main()
