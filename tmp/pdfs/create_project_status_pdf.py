from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT = Path("output/pdf/quantforge_project_status.pdf")


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def build() -> None:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleQF",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            textColor=colors.HexColor("#0B1F33"),
            spaceAfter=7 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubheadQF",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#46627F"),
            spaceAfter=8 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeadingQF",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0B1F33"),
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyQF",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1E2935"),
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellQF",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=11,
            textColor=colors.HexColor("#1E2935"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CellBoldQF",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=11,
            textColor=colors.HexColor("#0B1F33"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeaderCellQF",
            parent=styles["CellBoldQF"],
            textColor=colors.white,
        )
    )

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title="QuantForge Project Status",
        author="QuantForge",
    )
    story = [
        paragraph("QuantForge Project Status", styles["TitleQF"]),
        paragraph("Implementation assessment - 20 August 2026", styles["SubheadQF"]),
    ]

    metrics = Table(
        [
            [
                paragraph("Software foundation", styles["CellBoldQF"]),
                paragraph("~40% implemented", styles["CellBoldQF"]),
            ],
            [
                paragraph("Production readiness", styles["CellBoldQF"]),
                paragraph("~20-25% achieved", styles["CellBoldQF"]),
            ],
        ],
        colWidths=[78 * mm, 78 * mm],
        hAlign="LEFT",
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF3F8")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#86A9BF")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBD1DF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2 * mm),
            ]
        )
    )
    story += [metrics, Spacer(1, 7 * mm)]
    story += [paragraph("Assessment", styles["HeadingQF"])]
    story += [
        paragraph(
            "QuantForge has meaningful research and risk building blocks, but it "
            "intentionally lacks the execution, operations, and forward evidence "
            "required to use capital safely. The lower readiness figure is therefore "
            "expected: implementation progress must not be mistaken for deployment "
            "authorization.",
            styles["BodyQF"],
        ),
        Spacer(1, 4 * mm),
    ]

    rows = [
        [
            paragraph("Roadmap area", styles["HeaderCellQF"]),
            paragraph("Status", styles["HeaderCellQF"]),
            paragraph("What exists / what remains", styles["HeaderCellQF"]),
        ],
        [
            paragraph("0.1 Foundation", styles["CellBoldQF"]),
            paragraph("100%", styles["CellQF"]),
            paragraph(
                "Architecture, policies, typed contracts, configuration, and "
                "documentation are in place.",
                styles["CellQF"],
            ),
        ],
        [
            paragraph("0.2 Data ingestion", styles["CellBoldQF"]),
            paragraph("~70%", styles["CellQF"]),
            paragraph(
                "MT5 CSV ingestion, dataset manifests, and quality checks exist. "
                "Governed durable storage and broader feed validation remain.",
                styles["CellQF"],
            ),
        ],
        [
            paragraph("0.3 Portfolio + risk gate", styles["CellBoldQF"]),
            paragraph("~55%", styles["CellQF"]),
            paragraph(
                "Position/P&L accounting and pure risk checks exist. Enforced "
                "decisions, durable journal, kill-switch orchestration, and "
                "reconciliation remain.",
                styles["CellQF"],
            ),
        ],
        [
            paragraph("0.4 Backtesting", styles["CellBoldQF"]),
            paragraph("~75%", styles["CellQF"]),
            paragraph(
                "Deterministic ORB/momentum replay, cost and bias controls, "
                "reporting, and validation work exist. End-to-end reproducible "
                "gate evidence remains.",
                styles["CellQF"],
            ),
        ],
        [
            paragraph("0.5 Research lifecycle", styles["CellBoldQF"]),
            paragraph("~45%", styles["CellQF"]),
            paragraph(
                "Research corpus, validation protocol, and chronological validation "
                "core exist. Promotion workflow and formal approvals remain.",
                styles["CellQF"],
            ),
        ],
        [
            paragraph("0.6 Paper execution", styles["CellBoldQF"]),
            paragraph("~10%", styles["CellQF"]),
            paragraph(
                "Read-only MT5 bridge groundwork exists. Approved-order adapter, "
                "idempotency, reconciliation, and operator runbook remain.",
                styles["CellQF"],
            ),
        ],
        [
            paragraph("0.7-1.0 Operations", styles["CellBoldQF"]),
            paragraph("~0-5%", styles["CellQF"]),
            paragraph(
                "Policies point the way. Observability, alerting, drills, "
                "security/load reviews, and forward-test evidence remain.",
                styles["CellQF"],
            ),
        ],
    ]
    roadmap = Table(rows, colWidths=[37 * mm, 23 * mm, 96 * mm], repeatRows=1)
    roadmap.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B4F6C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C5D4DE")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F4F8FA")],
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.6 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.6 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm),
            ]
        )
    )
    story += [KeepTogether([roadmap, Spacer(1, 5 * mm)])]
    story += [paragraph("Recommended next milestone", styles["HeadingQF"])]
    story += [
        paragraph(
            "Complete the governed paper-trading workflow: Trade Intent -> Risk "
            "Decision -> Approved Order -> Durable Journal -> Paper Execution -> "
            "Reconciliation. This turns today's isolated components into a "
            "non-bypassable, auditable path while preserving the project's no-live-"
            "trading posture.",
            styles["BodyQF"],
        )
    ]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#BBD1DF"))
        canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
        canvas.setFillColor(colors.HexColor("#46627F"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, 7.5 * mm, "QuantForge - Internal project assessment")
        canvas.drawRightString(A4[0] - 18 * mm, 7.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
