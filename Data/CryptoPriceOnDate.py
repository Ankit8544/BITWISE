import xloil as xlo
import aiohttp
import datetime as dt
from dateutil import parser

BINANCE_REST = "https://api.binance.com"


# ============================
# Universal Date Parser
# ============================

def excel_date_to_datetime(value):
    """
    Handles:
    - Excel serial dates
    - Any string date format
    - Date + time
    """

    # Excel numeric date
    if isinstance(value, (int, float)):
        base = dt.datetime(1899, 12, 30)  # Excel epoch
        return base + dt.timedelta(days=float(value))

    # String date (ANY format)
    if isinstance(value, str):
        return parser.parse(value, dayfirst=False)

    # Already datetime
    if isinstance(value, dt.datetime):
        return value

    raise ValueError("Unsupported date format")


def to_ms(d: dt.datetime) -> int:
    """Convert datetime → UTC milliseconds"""
    if d.tzinfo is None:
        return int(d.timestamp() * 1000)
    return int(d.astimezone(dt.timezone.utc).timestamp() * 1000)


# ============================
# xlOil Function
# ============================

@xlo.func
async def CryptoPriceOnDate(
    symbol: str,
    date,
    interval: str = "1d",
    price_type: str = "close"
):
    """
    Get crypto price from Binance for ANY date format

    price_type:
        open | high | low | close | volume
    """

    symbol = symbol.upper()
    price_type = price_type.lower()

    dt_obj = excel_date_to_datetime(date)

    start_ms = to_ms(dt_obj)

    # Candle duration logic
    if interval.endswith("m"):
        end_ms = start_ms + int(interval[:-1]) * 60 * 1000
    elif interval.endswith("h"):
        end_ms = start_ms + int(interval[:-1]) * 60 * 60 * 1000
    elif interval.endswith("d"):
        end_ms = start_ms + 24 * 60 * 60 * 1000
    else:
        end_ms = start_ms + 24 * 60 * 60 * 1000

    url = f"{BINANCE_REST}/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as r:
            r.raise_for_status()
            data = await r.json()

    if not data:
        return "No data"

    k = data[0]

    price_map = {
        "open":   float(k[1]),
        "high":   float(k[2]),
        "low":    float(k[3]),
        "close":  float(k[4]),
        "volume": float(k[5])
    }

    if price_type not in price_map:
        return "Invalid price_type"

    return price_map[price_type]
