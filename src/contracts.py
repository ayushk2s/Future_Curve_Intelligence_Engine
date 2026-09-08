"""
Step 2 — CONTRACT NORMALIZATION  (blueprint section 8)

The exchange provides a symbol like "GCZ26.CMX". The modeling layer must not
care about exchange symbology. It wants standard fields:

    underlying     = "GOLD"
    contract_month = "December"
    expiry         = 2026-12-29   (a real date)
    days_to_expiry = 113          (relative to some 'as of' date)

This module does only that translation. No downloading, no maths on prices.
Keeping it isolated means adding Silver / MCX / crypto later only adds
new rules here and nothing downstream changes.

Run it directly to see it parse the 5 gold contracts:  python src/contracts.py
"""

from dataclasses import dataclass
import datetime as dt
import pandas as pd

# Futures month codes are an industry standard (same across every exchange).
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}


def comex_gold_last_trade_date(year: int, month: int) -> dt.date:
    """
    COMEX gold rule: trading terminates on the 3rd-to-last business day of the
    delivery month. Approximate 'business day' as Mon-Fri and ignore US
    exchange holidays -- close enough for an MVP, and we note it as a known gap.
    """
    first = pd.Timestamp(year, month, 1)
    end_of_month = first + pd.offsets.MonthEnd(0)
    business_days = pd.bdate_range(first, end_of_month)
    return business_days[-3].date()


@dataclass
class Contract:
    raw_symbol: str          # "GCZ26.CMX"  -- keep the original, never throw it away
    underlying: str          # "GOLD"
    contract_month: str      # "December"
    month_num: int           # 12
    year: int                # 2026
    expiry: dt.date          # 2026-12-29

    def days_to_expiry(self, as_of: dt.date) -> int:
        return (self.expiry - as_of).days

    def year_fraction(self, as_of: dt.date) -> float:
        """Time to expiry in YEARS -- this is the T that goes into carry maths."""
        return self.days_to_expiry(as_of) / 365.0


def parse_comex_gold(symbol: str) -> Contract:
    """
    "GCZ26.CMX" -> Contract(...)

    Layout: 'GC' (root) + 1 month-code letter + 2-digit year + '.CMX' (venue).
    """
    core = symbol.split(".")[0]          # "GCZ26"
    if not core.startswith("GC"):
        raise ValueError(f"not a COMEX gold symbol: {symbol!r}")

    month_code = core[2]                 # "Z"
    year_2d = core[3:]                   # "26"

    if month_code not in MONTH_CODES:
        raise ValueError(f"bad month code {month_code!r} in {symbol!r}")

    month_num = MONTH_CODES[month_code]
    year = 2000 + int(year_2d)

    return Contract(
        raw_symbol=symbol,
        underlying="GOLD",
        contract_month=MONTH_NAMES[month_num],
        month_num=month_num,
        year=year,
        expiry=comex_gold_last_trade_date(year, month_num),
    )


if __name__ == "__main__":
    today = dt.date(2026, 9, 7)
    symbols = ["GCV26.CMX", "GCZ26.CMX", "GCG27.CMX", "GCJ27.CMX", "GCM27.CMX"]

    print(f"as of {today}\n")
    print(f"{'symbol':12s} {'underlying':10s} {'month':10s} {'expiry':12s} {'DTE':>5s} {'T (yrs)':>8s}")
    print("-" * 62)
    for s in symbols:
        c = parse_comex_gold(s)
        print(f"{c.raw_symbol:12s} {c.underlying:10s} {c.contract_month:10s} "
              f"{str(c.expiry):12s} {c.days_to_expiry(today):5d} {c.year_fraction(today):8.4f}")
