# config.py


# Default quote currency for CoinGecko calls
VS_CURRENCY = "usd"

# How many days of history to pull for bulk import
BULK_DAYS_BACK = 365

ENABLE_HOURLY = True  # set to False if you only want daily data



TOP15_TAG = "TOP15"
MEME_TAG  = "MEME_TOP5"
L1_TAG    = "L1_BLUECHIP"
DEFI_TAG  = "DEFI_BLUECHIP"


# ------------ CoinGecko category ------------


MEME_CATEGORY = "meme-token"
L1_CATEGORY   = "layer-1"
DEFI_CATEGORY = "decentralized-finance-defi"


# ------------ Table names  ------------

TABLE_PRICE_DAILY  = "crypto_asset_price_daily"
TABLE_PRICE_HOURLY = "crypto_asset_price_hourly"


# ------------ Job names for job_run_log ------------

GROUP_SELECTOR_JOB_NAME   = "group_selector"
BULK_IMPORT_JOB_NAME      = "bulk_import"
INCREMENTAL_ETL_JOB_NAME  = "incremental_etl"
