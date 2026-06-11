"""
Declarative data-quality engine over a Spark DataFrame.

Each rule (loaded from config/data_quality/*.yaml) is evaluated into a
CheckResult. Supported rule types: volume, completeness, range, set, regex,
uniqueness. The comparison is always "observed metric vs threshold", so results
are uniform and easy to report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


@dataclass
class CheckResult:
    name: str
    type: str
    severity: str  # "critical" | "warning"
    passed: bool
    observed: float
    threshold: float
    detail: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


class QualityMonitor:
    """Evaluate a list of rule dicts against a DataFrame."""

    def __init__(self, rules: list[dict]) -> None:
        self.rules = rules

    def evaluate(self, df: DataFrame) -> tuple[int, list[CheckResult]]:
        total = df.count()
        return total, [self._dispatch(rule, df, total) for rule in self.rules]

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _pct(n: int, total: int) -> float:
        return 0.0 if total == 0 else round(100.0 * n / total, 4)

    def _dispatch(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        fn = getattr(self, f"_check_{rule['type']}", None)
        if fn is None:
            return CheckResult(
                rule.get("name", rule["type"]), rule["type"],
                rule.get("severity", "warning"), False, 0, 0,
                f"unknown rule type '{rule['type']}'",
            )
        return fn(rule, df, total)

    # --- rule types -------------------------------------------------------
    def _check_volume(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        thr = rule.get("min_rows", 1)
        return CheckResult(
            rule["name"], "volume", rule.get("severity", "critical"),
            passed=total >= thr, observed=total, threshold=thr,
            detail=f"{total} rows (min {thr})",
        )

    def _check_completeness(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        cols = rule["columns"]
        max_null = rule.get("max_null_pct", 0.0)
        counts = df.agg(
            *[F.sum(F.col(c).isNull().cast("long")).alias(c) for c in cols]
        ).collect()[0].asDict()
        worst_col = max(cols, key=lambda c: counts[c] or 0)
        worst_pct = self._pct(counts[worst_col] or 0, total)
        return CheckResult(
            rule["name"], "completeness", rule.get("severity", "critical"),
            passed=worst_pct <= max_null, observed=worst_pct, threshold=max_null,
            detail=f"worst null column={worst_col} ({worst_pct}%)",
        )

    def _check_range(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        col = rule["column"]
        lo, hi = rule.get("min"), rule.get("max")
        cond = F.col(col).isNull()
        if lo is not None:
            cond = cond | (F.col(col) < lo)
        if hi is not None:
            cond = cond | (F.col(col) > hi)
        viol = df.filter(cond).count()
        pct = self._pct(viol, total)
        thr = rule.get("max_violation_pct", 0.0)
        return CheckResult(
            rule["name"], "range", rule.get("severity", "critical"),
            passed=pct <= thr, observed=pct, threshold=thr,
            detail=f"{viol} rows outside [{lo}, {hi}]",
        )

    def _check_set(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        col = rule["column"]
        allowed = rule["allowed"]
        viol = df.filter(F.col(col).isNull() | ~F.col(col).isin(allowed)).count()
        pct = self._pct(viol, total)
        thr = rule.get("max_violation_pct", 0.0)
        return CheckResult(
            rule["name"], "set", rule.get("severity", "critical"),
            passed=pct <= thr, observed=pct, threshold=thr,
            detail=f"{viol} rows not in {allowed}",
        )

    def _check_regex(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        col = rule["column"]
        pattern = rule["pattern"]
        viol = df.filter(F.col(col).isNull() | ~F.col(col).rlike(pattern)).count()
        pct = self._pct(viol, total)
        thr = rule.get("max_violation_pct", 0.0)
        return CheckResult(
            rule["name"], "regex", rule.get("severity", "critical"),
            passed=pct <= thr, observed=pct, threshold=thr,
            detail=f"{viol} rows not matching /{pattern}/",
        )

    def _check_uniqueness(
        self,
        rule: dict,
        df: DataFrame,
        total: int
    ) -> CheckResult:
        cols = rule["columns"]
        thr = rule.get("max_dup_pct", 0.0)
        distinct = df.select(*cols).distinct().count()
        dups = total - distinct
        pct = self._pct(dups, total)
        return CheckResult(
            rule["name"], "uniqueness", rule.get("severity", "warning"),
            passed=pct <= thr, observed=pct, threshold=thr,
            detail=f"{dups} duplicate rows on {cols}",
        )
