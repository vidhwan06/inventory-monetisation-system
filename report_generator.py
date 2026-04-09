from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def generate_pdf(results, filename="AssetFlow_Report.pdf"):
    """
    Generates a clean PDF report from analysis results.
    """

    # =========================
    # CREATE DOCUMENT
    # =========================
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # =========================
    # TITLE
    # =========================
    elements.append(Paragraph("AssetFlow Inventory Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    total_products = len(results)
    elements.append(Paragraph(f"Total Products Analyzed: {total_products}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    if total_products == 0:
        elements.append(Paragraph("No data available. Please upload inventory.", styles["Normal"]))
        doc.build(elements)
        return filename

    # =========================
    # SUMMARY METRICS
    # =========================
    total_opportunity = 0
    dead_stock_count = 0

    for r in results:
        decision = r.get("final_decision", {})
        demand = r.get("agents", {}).get("demand_agent", {})

        change = decision.get("expected_profit_change", 0) or 0
        total_opportunity += max(change, 0)

        if str(demand.get("category", "")).lower() == "dead_stock":
            dead_stock_count += 1

    elements.append(Paragraph(f"Revenue Opportunity: ₹{round(total_opportunity, 2)}", styles["Normal"]))
    elements.append(Paragraph(f"Dead Stock Items: {dead_stock_count}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # =========================
    # TABLE HEADER
    # =========================
    table_data = [
        ["Product", "Action", "Risk", "Expected Change"]
    ]

    # =========================
    # SORT + TABLE DATA
    # =========================
    sorted_results = sorted(
        results,
        key=lambda x: x.get("final_decision", {}).get("expected_profit_change", 0),
        reverse=True
    )

    for r in sorted_results[:10]:
        product = r.get("product", "Unknown")

        decision = r.get("final_decision", {})
        risk = r.get("agents", {}).get("risk_agent", {})

        action = decision.get("action") or decision.get("final_action") or "HOLD"
        risk_level = str(risk.get("level", "low")).title()
        change = decision.get("expected_profit_change", 0)

        table_data.append([
            str(product),
            str(action),
            str(risk_level),
            f"₹{round(change, 2)}"
        ])

    # =========================
    # CREATE TABLE
    # =========================
    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # =========================
    # TOP RECOMMENDATIONS
    # =========================
    sorted_items = sorted(
        results,
        key=lambda x: x.get("final_decision", {}).get("expected_profit_change", 0) or 0,
        reverse=True
    )

    top_items = sorted_items[:5]

    elements.append(Paragraph("Top Recommendations", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    for item in top_items:
        product = item.get("product", "Unknown")
        decision = item.get("final_decision", {})

        action = decision.get("final_action") or decision.get("action", "HOLD")
        impact = round(decision.get("expected_profit_change", 0), 2)
        urgency = decision.get("urgency", "N/A")
        timeline = decision.get("timeline", "N/A")
        explanation = decision.get("enhanced_explanation", "")

        elements.append(Paragraph(f"<b>Product:</b> {product}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Action:</b> {action}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Impact:</b> ₹{impact}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Urgency:</b> {urgency}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Timeline:</b> {timeline}", styles["Normal"]))

        if explanation:
            elements.append(Paragraph(f"<b>Insight:</b> {explanation}", styles["Normal"]))

        elements.append(Spacer(1, 12))

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    return filename