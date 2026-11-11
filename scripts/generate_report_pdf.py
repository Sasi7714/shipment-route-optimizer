"""Generate the assignment's three-page technical report without extra packages."""
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "technical_report.pdf"

PAGES = [
    (
        "Technical Report: Shipment Route Optimization",
        [
            "Problem and objective",
            "Logistics planners balance shipment cost, transit time, and reliability. This project is an explainable decision-support API that evaluates alternative routes and recommends the best route for stated priorities. It is a demonstration, not an operational routing engine.",
            "Dataset and system design",
            "The synthetic dataset contains 20 Indian origin-destination shipments and 60 route options. Each option records hubs, INR cost, transit days, delay probability, congestion risk, and geopolitical risk. CSV/Pandas load the data into SQLite; FastAPI exposes it; independent scoring, Pareto, and explanation modules make the logic testable.",
        ],
    ),
    (
        "Decision framework and explainability",
        [
            "Combined risk = 0.50 x delay probability + 0.30 x congestion risk + 0.20 x geopolitical risk. Every risk input is a 0-1 estimate. Delay gets the highest internal weight because it most directly affects delivery reliability.",
            "For each shipment, cost, transit time, and combined risk are min-max normalized, then inverted because lower is preferable: benefit = 1 - (value - minimum) / (maximum - minimum). Equal metric values receive benefit 1.",
            "The default final score is 0.40 x cost benefit + 0.30 x time benefit + 0.30 x risk benefit. Users can submit non-negative weights, normalized proportionally. The response ranks every route and explains the winner against the runner-up, making trade-offs visible rather than hiding them behind a score.",
        ],
    ),
    (
        "Multi-objective evaluation, limitations, and next steps",
        [
            "Pareto analysis minimizes cost, time, and combined risk independently. A route is excluded when another option is no worse on all objectives and better on at least one. The remaining non-dominated routes are valid alternatives: for example, a cheaper route may be slower than a more reliable air option.",
            "Automated tests verify the risk formula, priority-sensitive ranking, Pareto dominance, successful API responses, and invalid input handling. This evaluates consistency of the decision framework and demonstrates sensitivity to business priorities.",
            "All values are illustrative and static. A production version should use live carrier quotes, weather, traffic, port congestion, capacity, carbon constraints, calibrated risk estimates, audit history, authentication, and monitoring.",
        ],
    ),
]


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


streams = []
for heading, paragraphs in PAGES:
    lines = [heading, ""]
    for paragraph in paragraphs:
        lines.extend(textwrap.wrap(paragraph, width=86))
        lines.append("")
    commands = ["BT", "/F1 16 Tf", "72 750 Td", f"({escape(lines[0])}) Tj", "/F1 10 Tf", "0 -28 Td"]
    for line in lines[1:]:
        commands.extend((f"({escape(line)}) Tj", "0 -14 Td"))
    commands.append("ET")
    streams.append("\n".join(commands).encode("latin-1"))

objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
page_ids = []
for stream in streams:
    page_ids.append(len(objects) + 1)
    content_id = len(objects) + 2
    objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode())
    objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
objects[1] = ("<< /Type /Pages /Kids [" + " ".join(f"{page} 0 R" for page in page_ids) + f"] /Count {len(page_ids)} >>").encode()

pdf, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), [0]
for index, obj in enumerate(objects, start=1):
    offsets.append(len(pdf))
    pdf.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
xref = len(pdf)
pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
for offset in offsets[1:]:
    pdf.extend(f"{offset:010d} 00000 n \n".encode())
pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
OUT.write_bytes(pdf)
print(f"Created {OUT} ({len(PAGES)} pages)")
