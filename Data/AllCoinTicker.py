import xloil as xlo
import asyncio
import websockets
import json
import datetime as dt

BINANCE_WS = "wss://stream.binance.com:9443/ws/!ticker@arr"

# ---------------- Time Helper ----------------

def to_ist(ms):
    return dt.datetime.utcfromtimestamp(ms / 1000) + dt.timedelta(hours=5, minutes=30)

# ---------------- Normalize ------------------

def normalize(d):
    return {
        "Symbol": d["s"],
        "EventTimeIST": to_ist(d["E"]),
        "LastPrice": float(d["c"]),
        "PriceChange": float(d["p"]),
        "PriceChangePercent": float(d["P"]),
        "HighPrice": float(d["h"]),
        "LowPrice": float(d["l"]),
        "BaseVolume": float(d["v"]),
        "QuoteVolume": float(d["q"]),
        "NumberOfTrades": int(d["n"])
    }

HEADER = [
    "Symbol",
    "EventTimeIST",
    "LastPrice",
    "PriceChange",
    "PriceChangePercent",
    "HighPrice",
    "LowPrice",
    "BaseVolume",
    "QuoteVolume",
    "NumberOfTrades"
]

def as_row(d):
    return [
        d["Symbol"],
        d["EventTimeIST"],
        d["LastPrice"],
        d["PriceChange"],
        d["PriceChangePercent"],
        d["HighPrice"],
        d["LowPrice"],
        d["BaseVolume"],
        d["QuoteVolume"],
        d["NumberOfTrades"]
    ]

# ---------------- RTD FUNCTION ----------------

@xlo.func
async def AllCoinsTickerStream():
    """
    Excel:
    =AllCoinsTickerStream()
    """

    state = {}
    last_snapshot = None
    reconnect_delay = 5

    STATUS_ROW_LIVE = ["STREAM_STATUS", "LIVE"] + [""] * (len(HEADER) - 2)
    STATUS_ROW_DOWN = ["STREAM_STATUS", "DISCONNECTED"] + [""] * (len(HEADER) - 2)

    while True:
        try:
            async with websockets.connect(
                BINANCE_WS,
                ping_interval=20,
                ping_timeout=10
            ) as ws:

                async for raw in ws:
                    data = json.loads(raw)

                    for item in data:
                        d = normalize(item)
                        state[d["Symbol"]] = d

                    rows = [as_row(state[s]) for s in sorted(state)]
                    table = [HEADER] + rows + [STATUS_ROW_LIVE]

                    last_snapshot = table
                    yield table

        except Exception:
            # ❌ no Excel error
            if last_snapshot:
                fallback = last_snapshot[:-1] + [STATUS_ROW_DOWN]
                yield fallback

            await asyncio.sleep(reconnect_delay)
