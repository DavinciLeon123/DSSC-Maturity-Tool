"""Pydantic schemas for the Phase 16 report contract (RPRT-01-04).

Mirrors `assessment.py`'s plain-BaseModel convention — no `from_attributes`/
ORM config, since `ReportContract` is assembled by hand in
`build_report_contract` (report_generator.py), not returned directly from
an ORM instance. These types document the contract for openapi and for the
frontend fetch types (plan 16-04).

`ReportRead` (the old `ComplianceReport`-backed schema) is removed here —
it had zero call sites (confirmed via repo-wide grep) and predates the
Assessment/versioning model; `ComplianceReport`-based persistence itself is
retired per Plan 16-02 (RESEARCH Pitfall 2 / Open Question 1).
"""

from pydantic import BaseModel


class MaturityBand(BaseModel):
    id: str
    label: str
    min: float
    max: float
    color: str


class PriorityListItem(BaseModel):
    category_id: str
    name: str
    score: float
    band_id: str
    band_label: str
    band_color: str


class ReportContract(BaseModel):
    assessment_id: int
    version: int
    initiative: dict
    dimension_scores: list[dict]
    priority_list: list[PriorityListItem]
    radar_chart_svg: str
    maturity_bands: list[MaturityBand]
