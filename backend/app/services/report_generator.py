"""Jinja2-based HTML report generator for MAMI compliance reports."""

import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_RECOMMENDATIONS: dict[str, str] = {
    "HRA-1.1": "Unless highly sensitive, please consider making your scheme agreements publicly available.",
    "MRA-1.1": "Please consider publishing your scheme in a machine-readable format by having an actionable sandbox/demo for end-users to interact with.",
    "TA-1.1": "Please consider specifying the actor responsible for publishing and updating the scheme, and also specify allowed procedures/actions that the scheme authority can conduct for updating and publishing the scheme.",
    "HRA-1.2": "Please consider including conditions in the scheme agreement via various clauses, like settlement clauses, liability clauses or any force majeure clauses.",
    "MRA-1.2": "Please consider supporting an automatic way for flagging incidents and an automatic way to track progress of the started disputes.",
    "TA-1.2": "Please consider indicating what are the trust anchor(s) that parties can go to for dispute management.",
    "HRA-1.3": "Please consider providing traceability tools generating a human readable/actionable record that can be used to achieve legal clarity for any subsequent dispute handling.",
    "MRA-1.3": "Please consider providing traceability tools generating a machine readable/actionable record that can be used to achieve automatic flagging of incidents and aid in subsequent dispute handling.",
    "TA-1.3": "Please consider specifying a Trust Anchor responsible for the operation/provision of the traceability tools. Also, please consider specifying what is being traced in accordance with the scope of your scheme, to ensure clarity and transparency for the interacting participants and/or 3rd parties joining the scheme.",
    "HRA-2.1": "Please consider providing human readable/actionable information regarding your scheme participation, including onboarding and offboarding procedures (to the extent allowed by privacy & sensitivity conditions).",
    "MRA-2.1": "Please consider providing code/APIs and/or adjacent testbeds to technically support onboarding and offboarding procedures. Also, please consider to what extent you may publicly disclose the scheme participation, onboarding procedures and access to testbeds. Also, please consider having access management controls in place for any sensitive content, including clear access conditions.",
    "TA-2.1": "Please consider specifying trust anchors for onboarding and offboarding procedures.",
    "HRA-2.2": "Please consider providing information about existing participants of the scheme via a registry, with access rights limited by sensitivity conditions of the scheme.",
    "MRA-2.2": "Please consider providing a machine readable/actionable registry of participant endpoints.",
    "TA-2.2": "Please consider specifying Trust Anchors for registry services provision.",
    "HRA-3.1": "Please consider providing at least general information regarding data sets available to scheme participants to discover, understand, access and/or visit said data to the extent permitted by sensitivity & privacy conditions, and consider providing explicit descriptions about the access conditions. Also, please consider adhering to the FAIR principles.",
    "MRA-3.1": "Please consider ensuring that your member provide information about data/data sets in a machine readable/actionable way, enabling other participants to discover, understand, access and/or visit said data, under specific sensitivity & privacy conditions.",
    "TA-3.1": "Please consider specifying trust anchors used for metadata standards, and specifying trust anchors/credibility means for assurance in data characteristics relevant in the context.",
    "HRA-3.2": "Please consider NOT providing actual data UNLESS the specified access & usage conditions are met; these conditions should then be documented in a human readable/actionable form.",
    "MRA-3.2": "Please consider NOT providing actual data UNLESS the specified access & usage conditions are met AND during a request for data access/visiting an automatic (machine readable/actionable) procedure of authentication & authorization has been properly completed.",
    "TA-3.2": "Please consider specifying the Scheme Authority and/or governance mechanisms/procedures as a trust anchor to ensure participants have obtained trusted digital identity means for relying parties to use for authenticating & authorizing to provide data access.",
    "HRA-4.1": "Please consider providing (at least general) information regarding services available to the scheme participants and/or 3rd parties (to the extent permitted by sensitivity & privacy conditions).",
    "MRA-4.1": "Please consider ensuring you and/or your participants provide (at least general) information regarding services available to other participants and/or 3rd parties in a machine readable/actionable way (to the extent permitted by sensitivity & privacy conditions).",
    "TA-4.1": "Please consider specifying Trust Anchors for each service provided under the scheme.",
    "HRA-4.2": "Please consider NOT providing actual services UNLESS the specified provision conditions are met; such conditions should then be made human readable/actionable.",
    "MRA-4.2": "Please consider NOT providing actual services UNLESS the specified provision conditions are met and any automatic checks to authorize the provision of service are completed.",
    "TA-4.2": "Please consider establishing Scheme Authority and/or governance mechanisms & procedures to ensure that trusted service providers adhere to the scheme conditions.",
}

_ANSWER_LABEL_MAP = {
    "YES": "Yes",
    "NOT_THERE_YET": "Not yet",
    "NOT_APPLICABLE": "Not applicable",
}

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def generate_html_report(
    initiative: dict,
    answers: list[dict],
    findings: list[dict],
    evidence_by_code: dict,
    mami_config: dict,
) -> str:
    """Render the compliance report HTML from a Jinja2 template.

    Args:
        initiative: dict with name, organization, contact_name
        answers:    list of dicts with mami_code, answer_value, rationale
        findings:   list of dicts from score_all_answers (FINDING status only)
        evidence_by_code: dict mapping mami_code -> list of EvidenceURL objects
        mami_config: full MAMI framework config dict

    Returns:
        Rendered HTML string.
    """
    env = _get_jinja_env()
    template = env.get_template("report.html")

    now = datetime.utcnow()
    generated_at = f"{now.day} {now.strftime('%B %Y, %H:%M')} UTC"

    matrix = _build_matrix(answers, findings, mami_config)
    topic_structure = _build_topic_structure(mami_config)
    heatmap_rows = _build_heatmap_rows(matrix, topic_structure)
    not_yet_recommendations = _build_not_yet_recommendations(answers, mami_config)

    context = {
        "initiative": initiative,
        "generated_at": generated_at,
        "heatmap_rows": heatmap_rows,
        "not_yet_recommendations": not_yet_recommendations,
    }
    return template.render(**context)


def _build_matrix(answers: list[dict], findings: list[dict], mami_config: dict) -> dict:
    """Build nested dict: {category: {dimension: {code_id: status}}}."""
    finding_lookup = {f["mami_code"]: f for f in findings}
    answer_lookup = {a["mami_code"]: a for a in answers}

    categories = ["scheme", "participants", "data", "services"]
    dimensions = ["human_readable", "machine_readable", "trust_anchors"]
    matrix: dict = {cat: {dim: {} for dim in dimensions} for cat in categories}

    for code in mami_config.get("codes", []):
        code_id = code["id"]
        cat = code["category"]
        dim = code["dimension"]

        if cat not in matrix or dim not in matrix[cat]:
            continue

        if code_id in finding_lookup:
            # Answer was NOT_THERE_YET and produced a finding
            status = "not_yet"
        elif code_id in answer_lookup:
            a = answer_lookup[code_id]
            if a["answer_value"] == "NOT_APPLICABLE":
                status = "n_a"
            else:
                status = "yes"
        else:
            status = "unanswered"

        matrix[cat][dim][code_id] = status

    return matrix


def _build_findings_detail(
    answers: list[dict],
    findings: list[dict],
    evidence_by_code: dict,
    mami_config: dict,
) -> list[dict]:
    """Build per-finding detail list for the report template."""
    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}
    answer_lookup = {a["mami_code"]: a for a in answers}

    detail = []
    for f in findings:
        if f.get("status") != "FINDING":
            continue
        code = code_lookup.get(f["mami_code"], {})
        answer = answer_lookup.get(f["mami_code"], {})
        evidence = evidence_by_code.get(f["mami_code"], [])

        # Display answer value as human-readable label
        raw_answer = answer.get("answer_value", "")
        answer_label = {
            "YES": "Yes",
            "NOT_THERE_YET": "Not there yet",
            "NOT_APPLICABLE": "Not applicable",
        }.get(raw_answer, raw_answer)

        detail.append(
            {
                "mami_code": f["mami_code"],
                "severity": f.get("severity", ""),
                "description": code.get("description", ""),
                "moscow_level": code.get("moscow_level", ""),
                "answer_value": raw_answer,
                "answer_label": answer_label,
                "followup_selections": answer.get("followup_selections") or [],
                "followup_other": answer.get("followup_other") or "",
                "evidence": [
                    {"url": ev.url if hasattr(ev, "url") else ev.get("url", "")} for ev in evidence
                ],
                "next_steps": _suggest_next_steps(f.get("severity", ""), code),
            }
        )

    return detail


def _build_topic_structure(mami_config: dict) -> dict:
    """Build per-category topic order with code lists.

    Returns: {category: [{topic_id, topic_label, codes: [code_id]}]}
    Used by the frontend to render the expanded heatmap with topic rows.
    """
    structure: dict = {}
    seen: dict = {}  # category -> {topic_id -> index}

    for code in mami_config.get("codes", []):
        cat = code["category"]
        topic_id = code["topic"]
        topic_label = code.get("topic_label", topic_id)
        code_id = code["id"]

        if cat not in structure:
            structure[cat] = []
            seen[cat] = {}

        if topic_id not in seen[cat]:
            seen[cat][topic_id] = len(structure[cat])
            structure[cat].append({"topic_id": topic_id, "topic_label": topic_label, "codes": []})

        structure[cat][seen[cat][topic_id]]["codes"].append(code_id)

    return structure


def _aggregate_cell(cell: dict) -> str:
    statuses = list(cell.values())
    if not statuses:
        return "unanswered"
    if "not_yet" in statuses:
        return "not_yet"
    if "unanswered" in statuses:
        return "unanswered"
    if all(s == "n_a" for s in statuses):
        return "n_a"
    if "yes" in statuses:
        return "yes"
    return "unanswered"


def _build_heatmap_rows(matrix: dict, topic_structure: dict) -> dict:
    """Build {category: [{topic_label, human_readable, machine_readable, trust_anchors}]}."""
    dims = ["human_readable", "machine_readable", "trust_anchors"]
    result: dict = {}
    for cat, topics in topic_structure.items():
        result[cat] = []
        for topic in topics:
            row: dict = {"topic_label": topic["topic_label"]}
            for dim in dims:
                cell = {
                    code: matrix.get(cat, {}).get(dim, {}).get(code)
                    for code in topic["codes"]
                    if matrix.get(cat, {}).get(dim, {}).get(code)
                }
                row[dim] = _aggregate_cell(cell)
            result[cat].append(row)
    return result


def _build_not_yet_recommendations(answers: list[dict], mami_config: dict) -> list[dict]:
    """Return recommendations for every NOT_THERE_YET answer, in code order."""
    code_meta = {c["id"]: c for c in mami_config.get("codes", [])}
    result = []
    for a in answers:
        if a.get("answer_value") != "NOT_THERE_YET":
            continue
        code_id = a["mami_code"]
        rec_key = re.sub(r"^[A-Z]+-", "", code_id)
        rec_text = _RECOMMENDATIONS.get(rec_key)
        if not rec_text:
            continue
        meta = code_meta.get(code_id, {})
        result.append(
            {
                "dimension_label": meta.get("dimension_label", ""),
                "topic_label": meta.get("topic_label", code_id),
                "text": rec_text,
            }
        )
    return result


def generate_report_data(
    initiative,
    answers: list[dict],
    findings: list[dict],
    evidence_by_code: dict,
    mami_config: dict,
) -> dict:
    """Return structured JSON-serialisable report data for the React /report page.

    Args:
        initiative: Initiative ORM object (or dict) with id, name attributes
        answers:    list of dicts with mami_code, answer_value, followup_selections, followup_other
        findings:   list of dicts from score_all_answers (FINDING status only)
        evidence_by_code: dict mapping mami_code -> list of EvidenceURL objects or dicts
        mami_config: full MAMI framework config dict

    Returns:
        Dict matching the JSON report shape expected by the React /report page.
    """
    code_lookup = {c["id"]: c for c in mami_config.get("codes", [])}

    # Resolve initiative id and name (supports ORM object or dict)
    if hasattr(initiative, "id"):
        initiative_id = str(initiative.id)
        initiative_name = initiative.name
    else:
        initiative_id = str(initiative.get("id", ""))
        initiative_name = initiative.get("name", "")

    return {
        "initiative": {
            "id": initiative_id,
            "name": initiative_name,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "matrix": _build_matrix(answers, findings, mami_config),
        "topic_structure": _build_topic_structure(mami_config),
        "answers": [
            {
                "mami_code": a["mami_code"],
                "answer_value": a["answer_value"],
                "answer_label": _ANSWER_LABEL_MAP.get(a["answer_value"], a["answer_value"]),
                "description": code_lookup.get(a["mami_code"], {}).get("description", ""),
                "followup_selections": a.get("followup_selections") or [],
                "followup_other": a.get("followup_other") or "",
                "evidence": [
                    {"url": ev.url if hasattr(ev, "url") else ev.get("url", "")}
                    for ev in evidence_by_code.get(a["mami_code"], [])
                ],
            }
            for a in answers
        ],
    }


def _suggest_next_steps(severity: str, code: dict) -> str:
    """Generate actionable next steps text based on severity and code metadata."""
    desc = code.get("description", "this requirement")
    if severity == "CRITICAL":
        return (
            f"This is a MUST requirement. Address '{desc}' to achieve compliance. "
            "MAMI framework mandates this for full certification."
        )
    return (
        f"This is a recommended improvement. Consider addressing '{desc}' "
        "to strengthen your compliance posture."
    )
