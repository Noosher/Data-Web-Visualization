# bulk_import.py

import os
import json
from datetime import datetime, timezone, timedelta
from collections import OrderedDict

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from config import (
    VS_CURRENCY,
    BULK_DAYS_BACK,         # used for DAILY history (e.g. 365)
    TABLE_PRICE_DAILY,
    TABLE_PRICE_HOURLY,
    BULK_IMPORT_JOB_NAME,
    ENABLE_HOURLY,
    HOURLY_MIN_AGE_HOURS,   # controls "every ~3 hours"
    DAILY_MIN_AGE_HOURS,    # controls "once per day"
    HOURLY_MAX_DAYS_BACK
)

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
    """
    Wrapper around /coins/{id}/market_chart?days=N

    - For DAILY data: works for any N; CoinGecko will downsample >90d to daily.
    - For HOURLY data: we explicitly cap N <= 90, so we always get hourly bars.
    """
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
    # Zip can truncate if lists are uneven, but CoinGecko usually syncs them.
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


# -------------------------
# Series fetchers
# -------------------------

def fetch_daily_series(coin_id: str, days: int):
    days = max(1, min(days, BULK_DAYS_BACK))
    payload = fetch_market_chart_raw(coin_id, VS_CURRENCY, days)
    rows = _parse_market_chart_to_rows(payload)

    # Collapse to one row per calendar date (last point wins)
    by_date: OrderedDict[datetime.date, dict] = OrderedDict()
    for r in rows:
        d = r["observed_at"].date()
        by_date[d] = r

    daily_rows = list(by_date.values())
    daily_rows.sort(key=lambda r: r["observed_at"])
    return daily_rows


def fetch_hourly_series(coin_id: str, days: int):
    days = max(1, min(days, HOURLY_MAX_DAYS_BACK))  # hard cap at 90d
    payload = fetch_market_chart_raw(coin_id, VS_CURRENCY, days)
    rows = _parse_market_chart_to_rows(payload)
    return rows


# -------------------------
# DB helpers
# -------------------------

def get_active_assets(conn):
    sql = text("""
        SELECT
            id,
            coingecko_id,
            symbol,
            name,
            last_daily_observed_at,
            last_hourly_observed_at
        FROM crypto_asset
        WHERE is_active = TRUE;
    """)
    result = conn.execute(sql)
    return [dict(row._mapping) for row in result.fetchall()]


def compute_days_to_pull_generic(last_ts, max_days: int) -> int:
    """
    Common logic for daily/hourly:
      - last_ts is NULL         -> full max_days
      - last_ts older than max  -> full max_days
      - last_ts within max      -> delta_days + 2 (buffer), clipped
    """
    now = datetime.now(timezone.utc)
    if last_ts is None:
        return max_days

    delta_days = (now - last_ts).days
    if delta_days >= max_days:
        return max_days

    return min(max_days, max(1, delta_days + 2))


def compute_daily_days_to_pull(last_daily_ts):
    # Daily can look back as far as BULK_DAYS_BACK (e.g. 365 days)
    return compute_days_to_pull_generic(last_daily_ts, BULK_DAYS_BACK)


def compute_hourly_days_to_pull(last_hourly_ts):
    return compute_days_to_pull_generic(last_hourly_ts, HOURLY_MAX_DAYS_BACK)


def should_run_hourly(last_hourly_ts, now: datetime) -> bool:
    if last_hourly_ts is None:
        return True  # never run before -> backfill (up to 90 days)
    age_hours = (now - last_hourly_ts).total_seconds() / 3600.0
    return age_hours >= HOURLY_MIN_AGE_HOURS


def should_run_daily(last_daily_ts, now: datetime) -> bool:
    if last_daily_ts is None:
        return True  # never run before -> backfill (up to BULK_DAYS_BACK)
    age_hours = (now - last_daily_ts).total_seconds() / 3600.0
    return age_hours >= DAILY_MIN_AGE_HOURS


def bulk_insert_prices_and_update_last_observed(
    conn,
    asset_id,
    coin_id: str,
    days_for_daily: int | None,
    days_for_hourly: int | None,
):
    # ---- Fetch daily ----
    daily_rows = []
    if days_for_daily is not None:
        daily_rows = fetch_daily_series(coin_id, days_for_daily)
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
            conn.execute(insert_daily_sql, [
                {
                    "asset_id": asset_id,
                    "observed_at": r["observed_at"],
                    "currency_code": VS_CURRENCY.upper(),
                    "price": r["price"],
                    "market_cap_usd": r["market_cap_usd"],
                    "volume_24h_usd": r["volume_24h_usd"],
                }
                for r in daily_rows
            ])

    # ---- Fetch hourly (optional) ----
    hourly_rows = []
    hourly_error = None
    if ENABLE_HOURLY and days_for_hourly is not None:
        try:
            hourly_rows = fetch_hourly_series(coin_id, days_for_hourly)
            if hourly_rows:
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
                conn.execute(insert_hourly_sql, [
                    {
                        "asset_id": asset_id,
                        "observed_at": r["observed_at"],
                        "currency_code": VS_CURRENCY.upper(),
                        "price": r["price"],
                        "market_cap_usd": r["market_cap_usd"],
                        "volume_24h_usd": r["volume_24h_usd"],
                    }
                    for r in hourly_rows
                ])
        except Exception as ex:
            hourly_error = str(ex)
            hourly_rows = []

    if daily_rows:
        last_daily_ts = daily_rows[-1]["observed_at"]
        conn.execute(text("""
            UPDATE crypto_asset
            SET last_daily_observed_at = :last_ts
            WHERE id = :asset_id
              AND (last_daily_observed_at IS NULL OR last_daily_observed_at < :last_ts);
        """), {"asset_id": asset_id, "last_ts": last_daily_ts})

    if hourly_rows:
        last_hourly_ts = hourly_rows[-1]["observed_at"]
        conn.execute(text("""
            UPDATE crypto_asset
            SET last_hourly_observed_at = :last_ts
            WHERE id = :asset_id
              AND (last_hourly_observed_at IS NULL OR last_hourly_observed_at < :last_ts);
        """), {"asset_id": asset_id, "last_ts": last_hourly_ts})

    return {
        "daily_rows": len(daily_rows),
        "hourly_rows": len(hourly_rows),
        "hourly_error": hourly_error,
    }


def update_job_run_log(conn, status: str, details=None):
    sql = text("""
        INSERT INTO job_run_log (job_name, last_run_at, last_status, details)
        VALUES (:job_name, NOW(), :status, CAST(:details AS JSONB))
        ON CONFLICT (job_name)
        DO UPDATE SET
            last_run_at = EXCLUDED.last_run_at,
            last_status = EXCLUDED.last_status,
            details     = EXCLUDED.details;
    """)
    conn.execute(sql, {
        "job_name": BULK_IMPORT_JOB_NAME,
        "status": status,
        "details": json.dumps(details) if details else None,
    })


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
        print("No active assets.")
        with engine.begin() as conn:
            update_job_run_log(conn, "success", {"asset_count": 0})
        return

    summary = {
        "asset_count": len(assets),
        "per_asset_rows": {},
        "errors": {},
    }

    # Step 2: per-asset decisions (daily/hourly) + load
    for asset in assets:
        now = datetime.now(timezone.utc)

        last_daily = asset["last_daily_observed_at"]
        last_hourly = asset["last_hourly_observed_at"]

        run_daily = should_run_daily(last_daily, now)
        run_hourly = ENABLE_HOURLY and should_run_hourly(last_hourly, now)

        if not run_daily and not run_hourly:
            print(f"Skipping {asset['symbol']} - fresh.")
            continue

        days_daily = compute_daily_days_to_pull(last_daily) if run_daily else None
        days_hourly = compute_hourly_days_to_pull(last_hourly) if run_hourly else None

        print(
            f"\n=== Bulk importing {asset['name']} ({asset['symbol']}) "
            f"[{asset['coingecko_id']}] (D:{days_daily}, H:{days_hourly}) ==="
        )

        try:
            with engine.begin() as conn:
                counts = bulk_insert_prices_and_update_last_observed(
                    conn,
                    asset_id=asset["id"],
                    coin_id=asset["coingecko_id"],
                    days_for_daily=days_daily,
                    days_for_hourly=days_hourly,
                )

            summary["per_asset_rows"][asset["coingecko_id"]] = counts
            print(
                f" -> Inserted {counts['daily_rows']} daily, "
                f"{counts['hourly_rows']} hourly."
            )
            if counts.get("hourly_error"):
                print(f"    Hourly error: {counts['hourly_error']}")

        except Exception as e:
            summary["errors"][asset["coingecko_id"]] = str(e)
            print(f" -> ERROR: {e}")

    # Step 3: log run
    status = "success" if not summary["errors"] else "partial_success"
    with engine.begin() as conn:
        update_job_run_log(conn, status, summary)

    print("\nDone.")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run_bulk_import()
