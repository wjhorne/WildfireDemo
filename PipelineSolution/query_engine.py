"""Plain-language query parser for the wildfire strategy pipeline.

Extracts the optimization request, objective, and simulation parameter overrides
from a natural-language query like:

    "Given the example terrain and 3 firefighters, best strategy to minimize
     burned area, firefighters starting at 5,5 and 25,25, fire at 30,30."
"""
from __future__ import annotations

import re
from typing import Any


_PAIR_RE = re.compile(r"(\d+)\s*,\s*(\d+)")


def _parse_pairs(text: str) -> list[tuple[int, int]]:
    return [(int(a), int(b)) for a, b in _PAIR_RE.findall(text)]


class QueryParser:
    """Parse a plain-language query into structured parameters."""

    def parse(self, query: str) -> dict[str, Any]:
        q = query.lower().strip()

        intent = self._extract_intent(q)
        objective = self._extract_objective(q)
        params = self._extract_parameters(q)
        validate = self._extract_validate(q)

        return {
            "intent": intent,
            "objective": objective,
            "params": params,
            "validate": validate,
        }

    def _extract_intent(self, q: str) -> str:
        if any(k in q for k in ("report", "pdf", "generate", "create", "plot", "analysis")):
            return "report"
        if any(k in q for k in ("validate", "baseline", "exact match", "example config")):
            return "validate"
        return "optimize"

    def _extract_objective(self, q: str) -> str:
        # Baseline objective is burned area; "save fuel" maps to the same ranking
        # (minimize burned -> maximize remaining fuel).
        if "fuel" in q and "save" in q:
            return "burned_area"
        return "burned_area"

    def _extract_validate(self, q: str) -> bool:
        return any(k in q for k in ("validate", "baseline", "exact match", "example config"))

    def _extract_parameters(self, q: str) -> dict[str, Any]:
        params: dict[str, Any] = {}

        # Grid size
        m = re.search(r"(\d+)\s*x\s*(\d+)\s*(?:grid|cells?)?", q)
        if m:
            params["nx"] = int(m.group(1))
            params["ny"] = int(m.group(2))
        m = re.search(r"nx\s*[:=]\s*(\d+)", q)
        if m:
            params["nx"] = int(m.group(1))
        m = re.search(r"ny\s*[:=]\s*(\d+)", q)
        if m:
            params["ny"] = int(m.group(1))

        # Turns / steps
        for pat in (r"nt\s*[:=]\s*(\d+)", r"(\d+)\s+(?:steps|turns)", r"for\s+(\d+)\s+(?:steps|turns)"):
            m = re.search(pat, q)
            if m:
                params["nt"] = int(m.group(1))
                break

        # Seed
        m = re.search(r"seed\s*[:=]?\s*(\d+)", q)
        if m:
            params["seed"] = int(m.group(1))

        # Firefighter count
        m = re.search(r"(\d+)\s+firefighters?", q)
        if m:
            params["firefighter_count"] = int(m.group(1))
        m = re.search(r"firefighters?\s*[:=]\s*(\d+)", q)
        if m:
            params["firefighter_count"] = int(m.group(1))

        # Fire start(s): "fire at 30,30", "fire start 30,30", "ignites at 30,30"
        fire_starts: list[tuple[int, int]] = []
        for pat in (r"fire\s+(?:start(?:s)?\s+)?at\s+(\d+\s*,\s*\d+)",
                    r"fire[- ]start[s]?\s+(\d+\s*,\s*\d+)",
                    r"ignites?\s+at\s+(\d+\s*,\s*\d+)"):
            for mm in re.finditer(pat, q):
                fire_starts.append((int(mm.group(1).split(",")[0]), int(mm.group(1).split(",")[1])))
        if fire_starts:
            params["fire_starts"] = tuple(fire_starts)

        # Firefighter starts: "firefighters start at 5,5 and 25,25" / "starting at ..."
        ff_starts: list[tuple[int, int]] = []
        m = re.search(r"firefighters?\s+(?:start(?:s|ing)?\s+)(?:at\s+)?(.+)", q)
        if m:
            # Trim at common trailing clauses so we don't swallow other params.
            tail = re.split(r"\b(?:with|seed|steps|turns|grid|minimize|best|strategy|to)\b", m.group(1))[0]
            ff_starts = _parse_pairs(tail)
        if ff_starts:
            params["firefighter_starts"] = tuple(ff_starts)

        # Fire dynamics
        for key, pat in {
            "p_ignite_low": r"p[_ ]ignite[_ ]low\s*[:=]\s*([0-9.]+)",
            "p_ignite_high": r"p[_ ]ignite[_ ]high\s*[:=]\s*([0-9.]+)",
            "p_extinguish": r"p[_ ]extinguish\s*[:=]\s*([0-9.]+)",
            "mountain_fraction": r"mountain[_ ]fraction\s*[:=]\s*([0-9.]+)",
            "water_fraction": r"water[_ ]fraction\s*[:=]\s*([0-9.]+)",
            "high_fuel_fraction": r"high[_ ]fuel[_ ]fraction\s*[:=]\s*([0-9.]+)",
        }.items():
            mm = re.search(pat, q)
            if mm:
                params[key] = float(mm.group(1))

        return params