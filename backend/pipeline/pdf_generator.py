"""
PDF export of the Security Incident Report.
Built with reportlab (pure-Python, no native system libraries) so it deploys
cleanly on Render without extra OS-level dependencies.
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from pipeline.sir_generator import MITRE_DESCRIPTIONS, VERDICT_ACTIONS

VERDICT_COLORS = {
    "TRUE_POSITIVE": colors.HexColor("#DC2626"),
    "FALSE_POSITIVE": colors.HexColor("#059669"),
    "NEEDS_REVIEW": colors.HexColor("#D97706"),
}

HEADER_BG = colors.HexColor("#1E293B")
ROW_ALT_BG = colors.HexColor("#F1F5F9")
GRID_COLOR = colors.HexColor("#CBD5E1")


def _table(data: list[list[str]], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def generate_pdf(
    ticket: dict[str, Any],
    llm_result: dict[str, Any],
    ml_result: dict[str, Any],
    similar_incidents: list[dict[str, Any]],
    guardrail_status: dict[str, str],
) -> bytes:
    """Build the Security Incident Report PDF and return its raw bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title=f"SIR-{ticket.get('ticket_id', 'unknown')}",
    )
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6, textColor=HEADER_BG
    )
    body_style = ParagraphStyle("Body", parent=styles["BodyText"], spaceAfter=4, leading=14)

    verdict = llm_result.get("verdict", "NEEDS_REVIEW")
    verdict_color = VERDICT_COLORS.get(verdict, colors.grey)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mitre_code = ticket.get("mitre_attack", "N/A")
    mitre_desc = MITRE_DESCRIPTIONS.get(mitre_code, "Unknown Technique")

    elements: list[Any] = []

    elements.append(Paragraph("SECURITY INCIDENT REPORT", styles["Title"]))
    elements.append(
        Paragraph(
            f"<font color='{verdict_color.hexval()}'><b>{verdict.replace('_', ' ')}</b></font>"
            f" &nbsp;&nbsp;|&nbsp;&nbsp; {ticket.get('ticket_id', 'N/A')} &nbsp;&nbsp;|&nbsp;&nbsp; Generated {generated_at}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Incident Overview", heading_style))
    elements.append(
        _table(
            [
                ["Field", "Value"],
                ["Ticket ID", ticket.get("ticket_id", "N/A")],
                ["Severity", ticket.get("severity", "N/A")],
                ["Verdict", verdict.replace("_", " ")],
                ["Risk Score", f"{llm_result.get('risk_score', 'N/A')} / 100"],
                ["Confidence", f"{llm_result.get('confidence', 0):.0%}"],
                ["Rule Triggered", ticket.get("rule_triggered", "N/A")],
                ["MITRE Technique", f"{mitre_code} — {mitre_desc}"],
                ["Affected User", f"{ticket.get('user', 'N/A')} ({ticket.get('user_type', 'N/A')})"],
                ["Source", f"{ticket.get('source_asset', 'N/A')} ({ticket.get('source_ip', 'N/A')})"],
                ["Target", f"{ticket.get('target_asset', 'N/A')} ({ticket.get('target_ip', 'N/A')})"],
                ["Detected", f"{ticket.get('day_of_week', 'N/A')} {ticket.get('hour_of_day', 'N/A')}:00"],
            ],
            col_widths=[140, 360],
        )
    )

    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(Paragraph(llm_result.get("reasoning", "No reasoning available."), body_style))

    elements.append(Paragraph("Root Cause Analysis", heading_style))
    elements.append(Paragraph(llm_result.get("root_cause", "Not determined from available data."), body_style))
    factors = llm_result.get("contributing_factors", [])
    if factors:
        for factor in factors:
            elements.append(Paragraph(f"&bull;&nbsp; {factor}", body_style))
    else:
        elements.append(Paragraph("No contributing factors identified.", body_style))

    elements.append(Paragraph("ML Analysis", heading_style))
    ml_verdict = ml_result.get("verdict", "UNKNOWN")
    ml_conf = ml_result.get("xgboost_score", ml_result.get("confidence", 0.5))
    elements.append(
        Paragraph(
            f"XGBoost classifier: <b>{ml_verdict}</b> ({ml_conf:.0%} confidence). "
            f"Key features: user_type={ticket.get('user_type', 'N/A')}, "
            f"historical_fp_count={ticket.get('historical_fp_count', 0)}, "
            f"historical_tp_count={ticket.get('historical_tp_count', 0)}.",
            body_style,
        )
    )

    elements.append(Paragraph("Indicators", heading_style))
    elements.append(
        _table(
            [
                ["Type", "Indicator"],
                ["Process", ticket.get("process", "N/A")],
                ["Command Line", _truncate(ticket.get("command_line", "N/A"))],
                ["Decoded Command", _truncate(ticket.get("decoded_command", "N/A"))],
                ["Source IP", ticket.get("source_ip", "N/A")],
                ["Target IP", ticket.get("target_ip", "N/A")],
                ["MITRE Technique", mitre_code],
            ],
            col_widths=[140, 360],
        )
    )

    if similar_incidents:
        elements.append(Paragraph("Similar Past Incidents", heading_style))
        rows = [["Ticket", "Verdict", "Similarity"]] + [
            [inc["ticket_id"], inc["verdict"], f"{inc['similarity']:.0%}"] for inc in similar_incidents
        ]
        elements.append(_table(rows, col_widths=[160, 160, 180]))

    elements.append(Paragraph("Recommended Action", heading_style))
    elements.append(Paragraph(VERDICT_ACTIONS.get(verdict, VERDICT_ACTIONS["NEEDS_REVIEW"]), body_style))

    elements.append(Paragraph("Guardrail Status", heading_style))
    elements.append(
        _table(
            [
                ["Check", "Status"],
                ["PII Scan", guardrail_status.get("presidio_pii_scan", "UNKNOWN")],
                ["Input Validation", guardrail_status.get("nemo_input_rail", "UNKNOWN")],
                ["Output Validation", guardrail_status.get("nemo_output_rail", "UNKNOWN")],
            ],
            col_widths=[140, 360],
        )
    )

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _truncate(text: str, limit: int = 200) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "…"
