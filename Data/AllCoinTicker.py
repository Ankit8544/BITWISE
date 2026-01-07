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

    state = {}   # symbol -> latest ticker

    async with websockets.connect(BINANCE_WS, ping_interval=20) as ws:
        async for raw in ws:
            data = json.loads(raw)

            for item in data:
                d = normalize(item)
                state[d["Symbol"]] = d

            # Yield FULL table every update
            rows = [as_row(state[s]) for s in sorted(state.keys())]
            yield [HEADER] + rows
