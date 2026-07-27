"""Admin cross-initiative aggregation service (ADMN-01).

Rebuilds the org-wide admin view for the new 6-category dimension-score
model: one org-wide averaged radar chart plus a per-initiative breakdown,
each initiative contributing only its latest SUBMITTED assessment (D-08).
Initiatives with zero submitted assessments are excluded from the org
average but still appear in the per-initiative list with `has_data=False`.

Reuses `generate_radar_svg` verbatim (D-01) — no second radar
implementation exists anywhere in this module.

STUB: RED phase (Task 1, tdd="true") — implementation to follow.
"""

from sqlmodel import Session


def build_admin_aggregate(session: Session, config: dict) -> dict:
    raise NotImplementedError("build_admin_aggregate not yet implemented (TDD RED phase)")
