from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


HEADERS = [
    "order_id",
    "city",
    "manager",
    "cleaner",
    "client_name",
    "client_phone",
    "address",
    "service_type",
    "price",
    "status",
    "scheduled_at",
    "created_at",
]


def export_csv(rows: list[dict], path: Path) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_xlsx(rows: list[dict], path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(HEADERS)
    for row in rows:
        ws.append([row.get(h, "") for h in HEADERS])
    wb.save(path)
    return path


def export_pdf(rows: list[dict], path: Path) -> Path:
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    c.setFont("Helvetica", 10)
    c.drawString(30, y, "Orders report")
    y -= 20
    for row in rows[:40]:
        line = f"#{row['order_id']} {row['city']} {row['service_type']} {row['price']} {row['status']}"
        c.drawString(30, y, line[:120])
        y -= 14
        if y < 50:
            c.showPage()
            y = 800
    c.save()
    return path
