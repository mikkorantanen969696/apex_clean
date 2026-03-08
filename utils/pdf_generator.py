from __future__ import annotations

from pathlib import Path

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def create_invoice_pdf(
    output_path: Path,
    qr_path: Path,
    order_id: int,
    client_name: str,
    service_type: str,
    amount: float,
    payment_link: str,
) -> Path:
    qr = qrcode.make(payment_link)
    qr.save(qr_path)

    c = canvas.Canvas(str(output_path), pagesize=A4)
    c.setFont("Helvetica", 13)
    c.drawString(20 * mm, 275 * mm, f"Invoice / Счет #{order_id}")
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, 265 * mm, f"Client: {client_name}")
    c.drawString(20 * mm, 257 * mm, f"Service: {service_type}")
    c.drawString(20 * mm, 249 * mm, f"Amount: {amount:.2f}")
    c.drawString(20 * mm, 241 * mm, "Scan QR for payment:")
    c.drawImage(str(qr_path), 20 * mm, 190 * mm, width=45 * mm, height=45 * mm)
    c.drawString(20 * mm, 183 * mm, payment_link)
    c.save()
    return output_path
