"""Big-number helpers.

* Gold is a Python ``int`` (unbounded precision).
* Combat values live in float64 numpy arrays and are clamped to MAXF (1e300),
  which is far beyond any realistic play session.
* ``fmt`` prints K, M, B, T, Qa ... Vg (1e63) and then falls back to scientific
  notation, and works for ints of any size.
"""
import math

MAXF = 1e300
SUFFIXES = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc", "Ud",
            "Dd", "Td", "Qad", "Qid", "Sxd", "Spd", "Ocd", "Nod", "Vg"]


def safe_pow(base, exp):
    try:
        v = base ** exp
    except OverflowError:
        return MAXF
    return MAXF if v > MAXF else v


def to_int(x):
    """float/int -> int, clamped & NaN-safe."""
    if isinstance(x, int):
        return x
    if x != x:
        return 0
    return int(min(x, MAXF))


def _mant(m):
    if m < 10:
        return f"{m:.2f}"
    if m < 100:
        return f"{m:.1f}"
    return f"{m:.0f}"


def fmt(x):
    """Human readable big number."""
    if isinstance(x, float):
        if x != x:
            return "NaN"
        if x == float("inf"):
            return "INF"
    neg = x < 0
    ax = -x if neg else x
    if ax < 1000:
        if ax < 10:
            s = f"{ax:.2f}".rstrip("0").rstrip(".")
        elif ax < 100:
            s = f"{ax:.1f}".rstrip("0").rstrip(".")
        else:
            s = f"{ax:.0f}"
        return ("-" if neg else "") + (s or "0")
    e = int(math.log10(ax))
    if ax / (10 ** e) >= 10:
        e += 1
    elif ax / (10 ** e) < 1:
        e -= 1
    tier = e // 3
    if tier < len(SUFFIXES):
        m = ax / (10 ** (tier * 3))
        s = _mant(m)
        if float(s) >= 1000:                       # 999.9K -> 1.00M
            tier += 1
            if tier < len(SUFFIXES):
                s = _mant(ax / (10 ** (tier * 3)))
        if tier < len(SUFFIXES):
            return ("-" if neg else "") + s + SUFFIXES[tier]
    m = ax / (10 ** e)
    return ("-" if neg else "") + f"{m:.2f}e{e}"
