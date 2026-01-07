import xloil
import asyncio
import time
import json
from websocket import create_connection
from datetime import datetime
import sys

Ticker_Field_Name = {
    "Event time": "E", # =TickerStream("btcusdt", "Event time")
    "Symbol": "s", # =TickerStream("btcusdt", "Symbol")
    "Price change": "p", # =TickerStream("btcusdt", "Price change")
    "Price change percent": "P", # =TickerStream("btcusdt", "Price change percent")
    "Weighted average price": "w", # =TickerStream("btcusdt", "Weighted average price")
    "Last price": "c", # =TickerStream("btcusdt", "Last price")
    "Last quantity": "Q", # =TickerStream("btcusdt", "Last quantity")
    "Open price": "o", # =TickerStream("btcusdt", "Open price")
    "High price": "h", # =TickerStream("btcusdt", "High price")
    "Low price": "l", # =TickerStream("btcusdt", "Low price")
    "Total traded base asset volume": "v", # =TickerStream("btcusdt", "Total traded base asset volume")
    "Total traded quote asset volume": "q", # =TickerStream("btcusdt", "Total traded quote asset volume")
    "Statistics open time": "O", # =TickerStream("btcusdt", "Statistics open time")
    "Statistics close time": "C", # =TickerStream("btcusdt", "Statistics close time")
    "First trade ID": "F", # =TickerStream("btcusdt", "First trade ID")
    "Last trade ID": "L", # =TickerStream("btcusdt", "Last trade ID")
    "Total number of trades": "n" # =TickerStream("btcusdt", "Total number of trades")
}

def safe_float(x):
    try:
        return None if x is None else float(x)
    except Exception:
        return None

def _format_ticker_value(key: str, val):
    """
    Normalize/format values based on Binance key:
      - timestamps (E, O, C) -> "YYYY-MM-DD HH:MM:SS" (UTC)
      - numeric strings -> float
      - integer ids/counters -> int
      - otherwise -> return original
    """
    if val is None:
        return None

    try:
        # timestamps in ms -> formatted datetime string
        if key in ("E", "O", "C"):
            # Binance sends epoch in milliseconds
            # convert to seconds and format as UTC
            ms = int(val)
            dt = datetime.utcfromtimestamp(ms / 1000.0)
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        # integer id/counters
        if key in ("F", "L", "n"):
            try:
                return int(val)
            except Exception:
                # fallback: try float->int
                return int(float(val))

        # numeric values: prices, volumes, quantities, percent
        if key in ("p", "P", "w", "c", "Q", "o", "h", "l", "v", "q"):
            # percent 'P' may be like "2.34" -> still float
            return safe_float(val)

        # symbol and others - return as-is
        return val

    except Exception:
        # if formatting fails, return original raw value
        return val

def BinanceTickerStream(symbol: str, field: str):
    while True:
        ws = None
        try:
            ws = create_connection(f"wss://stream.binance.com:9443/ws/{symbol}@ticker", timeout=10)
            while True:
                raw = ws.recv()
                if not raw:
                    raise RuntimeError("empty message / closed socket")
                try:
                    msg = json.loads(raw)
                except Exception:
                    # skip malformed frames
                    continue

                # Use the requested field key from the message
                if field in msg:
                    raw_value = msg.get(field)
                else:
                    # If user passed a friendly name (should already have been mapped),
                    # or the key doesn't exist, return an 'Invalid Field' marker.
                    raw_value = "Invalid Field"

                # Format the raw value into appropriate datatype/representation
                dynamic_value = _format_ticker_value(field, raw_value)

                yield dynamic_value

        except Exception as e:
            print(f"[live_btc_stream] websocket error: {e}. Reconnecting in 3s...")
            try:
                if ws:
                    ws.close()
            except Exception:
                pass
            time.sleep(3)
            continue
       
@xloil.func
async def TickerStream(symbol: str, field: str):
    """
    Stream a single Binance @ticker field to Excel.
    Accepts a human-friendly name (e.g. "High price") OR the raw Binance key (e.g. "h").
    """
    # map friendly name to Binance key if needed
    key = Ticker_Field_Name.get(field, field)

    # ensure symbol lowercased for Binance ws path
    res = BinanceTickerStream(symbol.lower(), key)

    try:
        while True:
            try:
                # run blocking generator in thread and await the result
                value = await asyncio.to_thread(next, res)
            except StopIteration:
                return

            # yield the concrete value back to Excel (string/number)
            yield value

            # breathe for the event loop
            await asyncio.sleep(0)

    except asyncio.CancelledError:
        # best-effort cleanup
        try:
            await asyncio.to_thread(getattr, res, "close")
        except Exception:
            pass
        return

    except Exception as e:
        # present error text to Excel instead of raising an exception
        yield f"Error: {e}"
        return

