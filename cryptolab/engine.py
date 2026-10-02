"""Analyze range liquidity, tick segments, inventory changes and impermanent loss across price trajectories."""

from decimal import Decimal, localcontext
from .validation import decimal, identifier


def inventory(liquidity, lower, upper, price):
    low = decimal(lower, positive=True).sqrt()
    high = decimal(upper, positive=True).sqrt()
    spot = decimal(price, positive=True).sqrt()
    amount = decimal(liquidity)
    if low >= high:
        raise ValueError("invalid price bounds")
    bounded = min(max(spot, low), high)
    return amount * (high - bounded) / (bounded * high), amount * (bounded - low)


def analyze(data):
    with localcontext() as ctx:
        ctx.prec = 60
        start = decimal(data["initial_price"], positive=True)
        positions = []
        ids = set()
        boundaries = set()
        for item in data["positions"]:
            name = identifier(item["id"])
            if name in ids:
                raise ValueError("duplicate position")
            ids.add(name)
            low = decimal(item["lower"], positive=True)
            high = decimal(item["upper"], positive=True)
            liquidity = decimal(item["liquidity"], positive=True)
            x, y = inventory(liquidity, low, high, start)
            positions.append(
                {
                    "id": name,
                    "lower": low,
                    "upper": high,
                    "liquidity": liquidity,
                    "initial_x": x,
                    "initial_y": y,
                }
            )
            boundaries.update((low, high))
        if not positions:
            raise ValueError("positions required")
        bounds = sorted(boundaries)
        segments = []
        for low, high in zip(bounds, bounds[1:]):
            midpoint = (low + high) / 2
            active = sum(
                (
                    p["liquidity"]
                    for p in positions
                    if p["lower"] <= midpoint < p["upper"]
                ),
                Decimal(0),
            )
            segments.append(
                {"lower": str(low), "upper": str(high), "active_liquidity": str(active)}
            )
        history = []
        previous = start
        fees = {p["id"]: Decimal(0) for p in positions}
        for step in data["trajectory"]:
            price = decimal(step["price"], positive=True)
            fee = decimal(step.get("fee_token1", 0))
            active = [p for p in positions if p["lower"] <= price < p["upper"]]
            total = sum((p["liquidity"] for p in active), Decimal(0))
            if fee and not total:
                raise ValueError("cannot allocate fees without active liquidity")
            for p in active:
                fees[p["id"]] += fee * p["liquidity"] / total
            crossed = [
                str(b)
                for b in bounds
                if min(previous, price) < b <= max(previous, price)
            ]
            snapshots = []
            for p in positions:
                x, y = inventory(p["liquidity"], p["lower"], p["upper"], price)
                value = x * price + y
                hold = p["initial_x"] * price + p["initial_y"]
                snapshots.append(
                    {
                        "id": p["id"],
                        "token0": str(x),
                        "token1": str(y),
                        "value_token1": str(value),
                        "hold_value_token1": str(hold),
                        "relative_loss": str(value / hold - 1) if hold else None,
                        "fee_token1": str(fees[p["id"]]),
                        "value_with_fees": str(value + fees[p["id"]]),
                    }
                )
            history.append(
                {
                    "price": str(price),
                    "active_liquidity": str(total),
                    "crossed_boundaries": crossed,
                    "positions": snapshots,
                }
            )
            previous = price
        return {
            "segments": segments,
            "trajectory": history,
            "position_count": len(positions),
            "total_allocated_fees": str(sum(fees.values())),
        }
