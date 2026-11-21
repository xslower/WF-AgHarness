from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Optional

from ..util.timeutil import clock, fmt_date
from .usage_db import COLS, UsageDb

pass
UnitPrice = Callable[[str], tuple[float, float]]

pass
pass
pass
USAGE_FLUSH_INTERVAL = 10 * 60

pass
CALIB_MIN, CALIB_MAX = 0.3, 6.0
pass
CALIB_MIN_ROWS = 5


class UsageTracker:

    def __init__(self, db_path: Path | None = None,
                 unit_price: Optional[UnitPrice] = None) -> None:
        pass
        self.db = UsageDb(db_path)
        pass
        self.unit_price = unit_price or (lambda _spec: (0.0, 0.0))
        self._lock = threading.Lock()
        pass
        self._cells: dict[tuple[str, str], list] = {}
        pass
        self._calib: dict[str, list] = {}
        pass
        self._tokens: dict[str, dict[str, int]] = {}
        pass
        self._day_cost: dict[str, float] = {}
        pass
        self._dirty: set[tuple[str, str]] = set()
        pass
        self._last_flush = clock()
        self._load()

    pass
    def _load(self) -> None:
        try:
            rows = self.db.load_all()
        except Exception:
            return
        for r in rows:
            day, spec = r["d"], r["spec"]
            cell = self._cells.setdefault((day, spec), [0] * 7)
            for i, name in enumerate(COLS):
                cell[i] = r[name] or 0
            if cell[4]:
                agg = self._calib.setdefault(spec, [0, 0, 0])
                agg[0] += cell[4]
                agg[1] += cell[5]
                agg[2] += cell[6]
            self._tokens.setdefault(day, {})[spec] = cell[1] + cell[2]
            self._day_cost[day] = self._day_cost.get(day, 0.0) + cell[3]

    pass
    def record(self, spec: str, session_id: str,
               prompt_tokens: int, completion_tokens: int,
               est: int = 0) -> None:
        price_in, price_out = self.unit_price(spec)
        pass
        cost = (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000
        with self._lock:
            self._apply(fmt_date(clock()), spec, int(prompt_tokens),
                        int(completion_tokens), cost, int(est or 0))
            due = clock() - self._last_flush >= USAGE_FLUSH_INTERVAL
        if due:
            pass
            self.maybe_flush()

    def maybe_flush(self) -> int:
        with self._lock:
            if not self._dirty:
                self._last_flush = clock()
                return 0
        n = self.flush()
        if n or not self._dirty:
            self._last_flush = clock()
        return n

    def _apply(self, day: str, spec: str, prompt: int, completion: int,
               cost: float, est: int) -> None:
        key = (day, spec)
        cell = self._cells.get(key)
        if cell is None:
            cell = self._cells[key] = [0] * 7
        cell[0] += 1
        cell[1] += prompt
        cell[2] += completion
        cell[3] += cost
        if est > 0 and prompt > 0:
            cell[4] += 1
            cell[5] += prompt
            cell[6] += est
            agg = self._calib.setdefault(spec, [0, 0, 0])
            agg[0] += 1
            agg[1] += prompt
            agg[2] += est
        else:
            self._calib.setdefault(spec, [0, 0, 0])
        per_day = self._tokens.setdefault(day, {})
        per_day[spec] = per_day.get(spec, 0) + prompt + completion
        self._day_cost[day] = self._day_cost.get(day, 0.0) + cost
        self._dirty.add(key)

    pass
    def flush(self) -> int:
        with self._lock:
            if not self._dirty:
                return 0
            rows = [(day, spec, *self._cells[(day, spec)])
                    for day, spec in self._dirty]
            try:
                n = self.db.upsert_many(rows)
            except Exception:
                return 0
            self._dirty.clear()
            return n

    def close(self) -> None:
        try:
            self.flush()
        finally:
            self.db.close()

    pass
    def today_tokens(self, spec: str) -> int:
        today = fmt_date(clock())
        with self._lock:
            return self._tokens.get(today, {}).get(spec, 0)

    def calibration(self, spec: str) -> float:
        with self._lock:
            rows, real, est = self._calib.get(spec, (0, 0, 0))
        if rows < CALIB_MIN_ROWS or not est:
            return 1.0
        return max(CALIB_MIN, min(CALIB_MAX, real / est))

    def summary(self, aliases: dict[str, str] | None = None) -> dict:
        alias = {k: v for k, v in (aliases or {}).items() if k and v}
        today = fmt_date(clock())
        by_provider: dict[str, dict] = {}
        with self._lock:
            cells = [(d, s, list(c)) for (d, s), c in self._cells.items()]
            day_cost = dict(self._day_cost)
        for day, spec, c in cells:
            prov, _, model = spec.partition("/")
            prov = alias.get(prov, prov) or "(未知)"
            model = model or "(未标注模型)"
            bucket = by_provider.setdefault(prov, _bucket())
            _add(bucket["models"].setdefault(model, _empty()), c)
            _add(bucket, c)
        return {
            "by_provider": _sorted_deep(by_provider),
            "today_cost": round(day_cost.get(today, 0.0), 4),
            "total_cost": round(sum(v["cost"] for v in by_provider.values()), 4),
        }


def _empty() -> dict:
    return {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0}


def _bucket() -> dict:
    b = _empty()
    b["models"] = {}
    return b


def _add(bucket: dict, cell: list) -> None:
    bucket["calls"] += cell[0]
    bucket["prompt"] += cell[1]
    bucket["completion"] += cell[2]
    bucket["cost"] += cell[3]


def _sorted_deep(by_provider: dict) -> dict:
    out = {}
    for name in sorted(by_provider):
        v = by_provider[name]
        models = {m: {**x, "cost": round(x["cost"], 4)}
                  for m, x in sorted(v["models"].items())}
        out[name] = {**v, "cost": round(v["cost"], 4), "models": models}
    return out
