import xloil as xlo
import asyncio
import aiohttp
import websockets
import datetime as dt
import json

BINANCE_REST = "https://api.binance.com"
BINANCE_WS   = "wss://stream.binance.com:9443/ws"
DEFAULT_LIMIT = 200


# ------------------- Time Helpers -------------------

def to_ist(ms: int) -> dt.datetime:
    return dt.datetime.utcfromtimestamp(ms / 1000) + dt.timedelta(hours=5, minutes=30)


# ------------------- Normalizers -------------------

def normalize_rest_kline(k):
    return {
        "OpenTime": int(k[0]),
        "OpenDateTimeIST": to_ist(int(k[0])),
        "Open": float(k[1]),
        "High": float(k[2]),
        "Low": float(k[3]),
        "Close": float(k[4]),
        "Volume": float(k[5]),
        "CloseTime": int(k[6]),
        "CloseDateTimeIST": to_ist(int(k[6])),
        "QuoteAssetVolume": float(k[7]),
        "NumberOfTrades": int(k[8]),
        "TakerBuyBaseVol": float(k[9]),
        "TakerBuyQuoteVol": float(k[10]),
    }


def normalize_ws_kline(k):
    return {
        "OpenTime": int(k["t"]),
        "OpenDateTimeIST": to_ist(int(k["t"])),
        "Open": float(k["o"]),
        "High": float(k["h"]),
        "Low": float(k["l"]),
        "Close": float(k["c"]),
        "Volume": float(k["v"]),
        "CloseTime": int(k["T"]),
        "CloseDateTimeIST": to_ist(int(k["T"])),
        "QuoteAssetVolume": float(k["q"]),
        "NumberOfTrades": int(k["n"]),
        "TakerBuyBaseVol": float(k["V"]),
        "TakerBuyQuoteVol": float(k["Q"]),
    }


def as_row(d):
    return [
        d["OpenDateTimeIST"],
        d["Open"],
        d["High"],
        d["Low"],
        d["Close"],
        d["Volume"],
        d["CloseDateTimeIST"],
        d["QuoteAssetVolume"],
        d["NumberOfTrades"],
        d["TakerBuyBaseVol"],
        d["TakerBuyQuoteVol"],
    ]


HEADER = [
    "OpenDateTimeIST",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "CloseDateTimeIST",
    "QuoteAssetVolume",
    "NumberOfTrades",
    "TakerBuyBaseVol",
    "TakerBuyQuoteVol",
]


# ------------------- REST Fetch -------------------

async def fetch_klines(session, symbol, interval, limit):
    url = f"{BINANCE_REST}/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }
    async with session.get(url, params=params) as r:
        r.raise_for_status()
        raw = await r.json()

    return [normalize_rest_kline(k) for k in raw]


# ------------------- RTD Function -------------------

@xlo.func
async def KlineStream(symbol: str, interval: str, limit: int = DEFAULT_LIMIT):

    symbol = symbol.upper()
    ws_url = f"{BINANCE_WS}/{symbol.lower()}@kline_{interval}"

    reconnect_delay = 5
    last_snapshot = None

    STATUS_ROW_LIVE = ["STREAM_STATUS", "LIVE"] + [""] * (len(HEADER) - 2)
    STATUS_ROW_DOWN = ["STREAM_STATUS", "DISCONNECTED"] + [""] * (len(HEADER) - 2)

    while True:
        try:
            async with aiohttp.ClientSession() as session:

                # ---------- Initial REST Load ----------
                rest_data = await fetch_klines(session, symbol, interval, limit)
                klines = {d["OpenTime"]: d for d in rest_data}

                def enforce_limit():
                    if len(klines) > limit:
                        excess = len(klines) - limit
                        for t in sorted(klines.keys())[:excess]:
                            del klines[t]

                def sorted_rows():
                    return [as_row(klines[t]) for t in sorted(klines.keys())]

                enforce_limit()
                table = [HEADER] + sorted_rows() + [STATUS_ROW_LIVE]
                last_snapshot = table
                yield table

                # ---------- WebSocket Stream ----------
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as ws:

                    async for raw in ws:
                        msg = json.loads(raw)

                        if "k" not in msg:
                            continue

                        k = msg["k"]
                        d = normalize_ws_kline(k)

                        klines[d["OpenTime"]] = d
                        enforce_limit()

                        table = (
                            [HEADER]
                            + sorted_rows()
                            + [STATUS_ROW_LIVE]
                        )
                        last_snapshot = table
                        yield table

                        # ---------- On Candle Close ----------
                        if k.get("x", False):
                            fresh = await fetch_klines(
                                session, symbol, interval, limit
                            )
                            for row in fresh:
                                klines[row["OpenTime"]] = row

                            enforce_limit()
                            table = (
                                [HEADER]
                                + sorted_rows()
                                + [STATUS_ROW_LIVE]
                            )
                            last_snapshot = table
                            yield table

        except Exception:
            # ❌ Excel ko error mat dikhao
            # 🧊 last data freeze rahe
            if last_snapshot:
                fallback = last_snapshot[:-1] + [STATUS_ROW_DOWN]
                yield fallback

            # ⏳ sirf error ke baad wait
            await asyncio.sleep(reconnect_delay)


