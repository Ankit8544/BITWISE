import xloil as xlo
import aiohttp
import websockets
import datetime as dt
import json
import time   # ✅ ADDED (ONLY NEW IMPORT)

# ============================
# Binance Endpoints
# ============================

BINANCE_REST = "https://api.binance.com"
BINANCE_WS   = "wss://stream.binance.com:9443/ws"

# ============================
# Time Helpers
# ============================

def to_ist(ms: int) -> dt.datetime:
    return dt.datetime.utcfromtimestamp(ms / 1000) + dt.timedelta(hours=5, minutes=30)

# ============================
# Normalizers
# ============================

def normalize_aggtrade(t: dict) -> dict:
    return {
        "TradeTimeIST": to_ist(int(t["T"])),
        "Price": float(t["p"]),
        "Quantity": float(t["q"]),
        "AggTradeID": int(t["a"]),
        "FirstTradeID": int(t["f"]),
        "LastTradeID": int(t["l"]),
        "IsBuyerMaker": t["m"],
        "IsBestMatch": t["M"]
    }

# ============================
# Table Helpers
# ============================

HEADER = [
    "TradeTimeIST",
    "Price",
    "Quantity",
    "AggTradeID",
    "FirstTradeID",
    "LastTradeID",
    "IsBuyerMaker",
    "IsBestMatch"
]

def as_row(d: dict) -> list:
    return [
        d["TradeTimeIST"],
        d["Price"],
        d["Quantity"],
        d["AggTradeID"],
        d["FirstTradeID"],
        d["LastTradeID"],
        d["IsBuyerMaker"],
        d["IsBestMatch"]
    ]

# ============================
# Time Window Filter
# ============================

def filter_by_time_window(trades: list, minutes: float) -> list:
    if not trades:
        return []

    latest = max(t["TradeTimeIST"] for t in trades)
    cutoff = latest - dt.timedelta(minutes=minutes)

    return [t for t in trades if t["TradeTimeIST"] >= cutoff]

# ============================
# REST BACKFILL
# ============================

async def fetch_aggtrades_looped(session, symbol, minutes, max_loops=6):

    url = f"{BINANCE_REST}/api/v3/aggTrades"
    trades = []
    from_id = None

    for _ in range(max_loops):

        params = {"symbol": symbol.upper(), "limit": 1000}
        if from_id is not None:
            params["fromId"] = from_id

        async with session.get(url, params=params) as r:
            r.raise_for_status()
            data = await r.json()

        if not data:
            break

        normalized = [normalize_aggtrade(t) for t in data]
        trades = normalized + trades
        from_id = int(data[0]["a"]) - 1000

        span = (
            max(t["TradeTimeIST"] for t in trades)
            - min(t["TradeTimeIST"] for t in trades)
        ).total_seconds() / 60

        if span >= minutes * 1.05:
            break

    return trades

# ============================
# XlOil Function
# ============================

@xlo.func
async def AggTradeStreamWindow2(symbol: str, minutes: float = 1.0, limit: int | None = None):

    symbol = symbol.upper()
    ws_url = f"{BINANCE_WS}/{symbol.lower()}@aggTrade"

    async with aiohttp.ClientSession() as session:

        trades = await fetch_aggtrades_looped(session, symbol, minutes, max_loops=100)

        last_id = max(t["AggTradeID"] for t in trades) if trades else -1

        filtered = filter_by_time_window(trades, minutes)
        yield [HEADER] + [as_row(t) for t in filtered]

        # ============================
        # 🔥 EXCEL THROTTLE (ONLY FIX)
        # ============================

        last_emit = 0.0
        EMIT_INTERVAL = 0.5   # seconds

        async with websockets.connect(ws_url, ping_interval=20) as ws:
            async for msg in ws:

                t = json.loads(msg)
                agg_id = int(t["a"])

                if agg_id <= last_id:
                    continue

                d = normalize_aggtrade(t)
                trades.append(d)
                last_id = agg_id

                if limit is not None and len(trades) > limit:
                    trades = trades[-limit:]

                now = time.time()

                if now - last_emit >= EMIT_INTERVAL:
                    filtered = filter_by_time_window(trades, minutes)
                    yield [HEADER] + [as_row(t) for t in filtered]
                    last_emit = now
