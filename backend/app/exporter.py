import io
import csv
import datetime
from typing import Dict, List

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

from icalendar import Calendar, Event, vText

from app.models import ScheduleResult, Match


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _footer_canvas(canvas, doc):
    """Draw a footer on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(
        A4[0] / 2,
        20,
        "Made with schedule-it.com",
    )
    canvas.restoreState()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def generate_pdf(result: ScheduleResult) -> bytes:
    """Generate a PDF fixture schedule and return it as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()
    story: List = []

    # Title
    title_style = styles["Title"]
    story.append(Paragraph("Fixture Schedule", title_style))
    generated_date = datetime.datetime.now().strftime("%d %B %Y")
    story.append(Paragraph(f"Generated: {generated_date}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Group matches by round
    rounds: Dict[int, List[Match]] = {}
    for match in result.matches:
        rounds.setdefault(match.round_num, []).append(match)

    for round_num in sorted(rounds.keys()):
        story.append(Paragraph(f"Round {round_num}", styles["Heading2"]))
        story.append(Spacer(1, 8))

        # Table header + rows
        table_data = [["Date", "Time", "Home Team", "Away Team", "Venue"]]
        for match in rounds[round_num]:
            table_data.append([
                match.date.strftime("%d/%m/%Y"),
                match.time.strftime("%H:%M"),
                match.home_team,
                match.away_team,
                match.venue,
            ])

        col_widths = [70, 50, 120, 120, 120]
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 16))

    # Quality metrics section
    story.append(PageBreak())
    story.append(Paragraph("Quality Metrics", styles["Heading1"]))
    story.append(Spacer(1, 12))

    m = result.metrics
    metrics_data = [
        ["Metric", "Value"],
        ["Violations", str(m.violations)],
        ["Home/Away Breaks", str(m.home_away_breaks)],
        ["Balance Score", f"{m.balance_score:.4f}"],
        ["Solve Status", m.status],
        ["Solve Time (ms)", str(m.solve_time_ms)],
        ["Total Rounds", str(result.total_rounds)],
        ["Total Matches", str(result.total_matches)],
    ]
    mt = Table(metrics_data, colWidths=[180, 180])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(mt)

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def generate_csv(result: ScheduleResult) -> bytes:
    """Generate a UTF-8-with-BOM CSV of all fixtures and return as bytes."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Round", "Date", "Time", "Home Team", "Away Team", "Venue", "Venue Capacity"])
    for match in result.matches:
        writer.writerow([
            match.round_num,
            match.date.strftime("%Y-%m-%d"),
            match.time.strftime("%H:%M"),
            match.home_team,
            match.away_team,
            match.venue,
            match.venue_capacity,
        ])

    # Encode with UTF-8 BOM so Excel opens it correctly
    return output.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# ICS
# ---------------------------------------------------------------------------

def generate_ics_per_team(result: ScheduleResult) -> Dict[str, bytes]:
    """
    Generate one .ics calendar file per team.
    Returns a dict keyed by team name, values are raw ICS bytes.
    """
    # Collect which matches each team is involved in
    team_matches: Dict[str, List[Match]] = {}
    for match in result.matches:
        for team in (match.home_team, match.away_team):
            team_matches.setdefault(team, []).append(match)

    calendars: Dict[str, bytes] = {}
    for team, matches in team_matches.items():
        cal = Calendar()
        cal.add("PRODID", vText("-//schedule-it.com//EN"))
        cal.add("VERSION", "2.0")
        cal.add("CALSCALE", "GREGORIAN")
        cal.add("X-WR-CALNAME", vText(f"{team} Fixtures"))

        for match in matches:
            event = Event()
            event.add("SUMMARY", vText(
                f"{match.home_team} vs {match.away_team} @ {match.venue}"
            ))

            # Combine date + time into a naive datetime
            dtstart = datetime.datetime.combine(match.date, match.time)
            dtend = dtstart + datetime.timedelta(minutes=90)
            event.add("DTSTART", dtstart)
            event.add("DTEND", dtend)

            event.add("LOCATION", vText(match.venue))
            event.add(
                "DESCRIPTION",
                vText(f"Round {match.round_num} \u2013 generated by schedule-it.com"),
            )

            cal.add_component(event)

        calendars[team] = cal.to_ical()

    return calendars
