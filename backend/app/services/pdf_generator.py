"""
T06: PDF Generator Service

Generate regulatory-compliant PDF documents for adverse action notices
and offering price disclosures.

Per tasks/T06_demo_polish.md
"""

from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Reason:
    """Adverse action reason with code and text."""
    code: str
    text: str


@dataclass
class CounterOffer:
    """Counter-offer terms for conditional decline."""
    adjusted_term_months: int
    adjusted_apr: float
    adjusted_monthly_payment: float
    required_down_payment: float


@dataclass
class AdverseActionNotice:
    """Adverse action notice data for PDF generation."""
    notice_id: str
    applicant_name: str
    decision_date: str
    bureau_source: str
    score_date: str
    reasons: List[Reason]
    counter_offer: Optional[CounterOffer] = None


@dataclass
class Addon:
    """Vehicle addon for offering price."""
    id: str
    name: str
    price: float


@dataclass
class OfferingPriceComponents:
    """Components of SB 766 offering price."""
    base_vehicle_price: float
    doc_fee: float
    mandatory_addons: List[Addon]
    total_offering_price: float


@dataclass
class Vehicle:
    """Vehicle info for PDF."""
    year: int
    make: str
    model: str
    trim: Optional[str] = None
    vin: Optional[str] = None


# Translation strings for PDFs
TRANSLATIONS = {
    "en": {
        "adverse_action": {
            "title": "ADVERSE ACTION NOTICE",
            "subtitle": "Statement of Credit Decision",
            "applicant": "Applicant",
            "date": "Decision Date",
            "reasons_title": "PRINCIPAL REASONS FOR THIS DECISION",
            "bureau_title": "CREDIT BUREAU INFORMATION",
            "bureau_source": "Bureau Source",
            "score_date": "Score Date",
            "counter_offer_title": "ALTERNATIVE TERMS AVAILABLE",
            "term": "Term",
            "apr": "APR",
            "payment": "Monthly Payment",
            "down_payment": "Required Down Payment",
            "footer": "This notice is provided in compliance with the Equal Credit Opportunity Act (Regulation B). You have the right to request the specific reasons for this decision within 60 days.",
            "fcra_notice": "Under the Fair Credit Reporting Act, you have the right to obtain a free copy of your credit report from the bureau listed above."
        },
        "offering_price": {
            "title": "OFFICIAL OFFERING PRICE DISCLOSURE",
            "vehicle_price": "Vehicle Price",
            "doc_fee": "Documentation Fee",
            "total": "TOTAL OFFERING PRICE",
            "notice": "Government taxes and registration fees are additional and calculated based on your location.",
            "sb766": "This disclosure complies with California SB 766."
        }
    },
    "es": {
        "adverse_action": {
            "title": "AVISO DE ACCIÓN ADVERSA",
            "subtitle": "Declaración de Decisión de Crédito",
            "applicant": "Solicitante",
            "date": "Fecha de Decisión",
            "reasons_title": "RAZONES PRINCIPALES DE ESTA DECISIÓN",
            "bureau_title": "INFORMACIÓN DEL BURÓ DE CRÉDITO",
            "bureau_source": "Fuente del Buró",
            "score_date": "Fecha del Puntaje",
            "counter_offer_title": "TÉRMINOS ALTERNATIVOS DISPONIBLES",
            "term": "Plazo",
            "apr": "APR",
            "payment": "Pago Mensual",
            "down_payment": "Pago Inicial Requerido",
            "footer": "Este aviso se proporciona en cumplimiento con la Ley de Igualdad de Oportunidad de Crédito (Regulación B). Tiene derecho a solicitar las razones específicas de esta decisión dentro de 60 días.",
            "fcra_notice": "Bajo la Ley de Informes de Crédito Justos, tiene derecho a obtener una copia gratuita de su informe de crédito del buró listado arriba."
        },
        "offering_price": {
            "title": "DIVULGACIÓN DE PRECIO DE OFERTA OFICIAL",
            "vehicle_price": "Precio del Vehículo",
            "doc_fee": "Cargo por Documentación",
            "total": "PRECIO DE OFERTA TOTAL",
            "notice": "Los impuestos gubernamentales y tarifas de registro son adicionales y se calculan según su ubicación.",
            "sb766": "Esta divulgación cumple con California SB 766."
        }
    }
}


class PDFGenerator:
    """
    Generate regulatory-compliant PDF documents.

    Uses simple text-based PDF generation for demo purposes.
    In production, would use reportlab or similar library.
    """

    def __init__(self):
        """Initialize PDF generator."""
        self.dealer_name = "Mini-Lakebed Demo Dealer"

    def generate_adverse_action_notice(
        self,
        notice: AdverseActionNotice,
        language: str = "en"
    ) -> BytesIO:
        """
        Generate Regulation B compliant adverse action notice PDF.

        Args:
            notice: AdverseActionNotice data
            language: Language code (en/es)

        Returns:
            BytesIO containing PDF content
        """
        t = TRANSLATIONS.get(language, TRANSLATIONS["en"])["adverse_action"]

        # Build PDF content as text (demo format)
        lines = []
        lines.append("=" * 60)
        lines.append(t["title"].center(60))
        lines.append(t["subtitle"].center(60))
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"{t['applicant']}: {notice.applicant_name}")
        lines.append(f"{t['date']}: {notice.decision_date}")
        lines.append(f"Notice ID: {notice.notice_id}")
        lines.append("")
        lines.append("-" * 60)
        lines.append(t["reasons_title"])
        lines.append("-" * 60)

        for i, reason in enumerate(notice.reasons[:4], 1):
            lines.append(f"  {i}. {reason.text} ({reason.code})")

        lines.append("")
        lines.append("-" * 60)
        lines.append(t["bureau_title"])
        lines.append("-" * 60)
        lines.append(f"  {t['bureau_source']}: {notice.bureau_source}")
        lines.append(f"  {t['score_date']}: {notice.score_date}")

        if notice.counter_offer:
            lines.append("")
            lines.append("-" * 60)
            lines.append(t["counter_offer_title"])
            lines.append("-" * 60)
            lines.append(f"  {t['term']}: {notice.counter_offer.adjusted_term_months} months")
            lines.append(f"  {t['apr']}: {notice.counter_offer.adjusted_apr}%")
            lines.append(f"  {t['payment']}: ${notice.counter_offer.adjusted_monthly_payment:.2f}")
            lines.append(f"  {t['down_payment']}: ${notice.counter_offer.required_down_payment:,.2f}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        # Word wrap footer
        footer = t["footer"]
        for i in range(0, len(footer), 55):
            lines.append(footer[i:i+55])
        lines.append("")
        fcra = t["fcra_notice"]
        for i in range(0, len(fcra), 55):
            lines.append(fcra[i:i+55])
        lines.append("")
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append(f"Dealer: {self.dealer_name}")

        # Create PDF-like content
        content = "\n".join(lines)

        # For demo purposes, return text content wrapped as "PDF"
        # In production, use reportlab to generate actual PDF
        buffer = BytesIO()
        buffer.write(b"%PDF-1.4\n")  # PDF header marker
        buffer.write(content.encode('utf-8'))
        buffer.write(b"\n%%EOF")  # PDF footer marker
        buffer.seek(0)

        return buffer

    def generate_offering_price_disclosure(
        self,
        vehicle: Vehicle,
        components: OfferingPriceComponents,
        language: str = "en"
    ) -> BytesIO:
        """
        Generate SB 766 compliant offering price disclosure PDF.

        Args:
            vehicle: Vehicle information
            components: Price breakdown components
            language: Language code (en/es)

        Returns:
            BytesIO containing PDF content
        """
        t = TRANSLATIONS.get(language, TRANSLATIONS["en"])["offering_price"]

        lines = []
        lines.append("=" * 60)
        lines.append(t["title"].center(60))
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Vehicle: {vehicle.year} {vehicle.make} {vehicle.model}")
        if vehicle.trim:
            lines.append(f"Trim: {vehicle.trim}")
        if vehicle.vin:
            lines.append(f"VIN: {vehicle.vin}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("PRICE BREAKDOWN")
        lines.append("-" * 60)
        lines.append(f"  {t['vehicle_price']:.<40} ${components.base_vehicle_price:>12,.2f}")
        lines.append(f"  {t['doc_fee']:.<40} ${components.doc_fee:>12,.2f}")

        for addon in components.mandatory_addons:
            lines.append(f"  {addon.name:.<40} ${addon.price:>12,.2f}")

        lines.append("-" * 60)
        lines.append(f"  {t['total']:.<40} ${components.total_offering_price:>12,.2f}")
        lines.append("=" * 60)
        lines.append("")
        # Word wrap notice
        notice = t["notice"]
        for i in range(0, len(notice), 55):
            lines.append(notice[i:i+55])
        lines.append("")
        lines.append(t["sb766"])
        lines.append("")
        lines.append(f"Generated: {datetime.utcnow().isoformat()}")
        lines.append(f"Dealer: {self.dealer_name}")

        content = "\n".join(lines)

        buffer = BytesIO()
        buffer.write(b"%PDF-1.4\n")
        buffer.write(content.encode('utf-8'))
        buffer.write(b"\n%%EOF")
        buffer.seek(0)

        return buffer


# Module-level singleton
_generator: Optional[PDFGenerator] = None


def get_pdf_generator() -> PDFGenerator:
    """Get or create the PDF generator singleton."""
    global _generator
    if _generator is None:
        _generator = PDFGenerator()
    return _generator


def generate_adverse_action_pdf(
    notice_data: Dict[str, Any],
    language: str = "en"
) -> BytesIO:
    """
    Convenience function to generate adverse action PDF.

    Args:
        notice_data: Dictionary with notice data
        language: Language code

    Returns:
        BytesIO containing PDF content
    """
    reasons = [
        Reason(code=r.get("code", ""), text=r.get("text", ""))
        for r in notice_data.get("reasons", [])
    ]

    counter_offer = None
    if "counter_offer" in notice_data and notice_data["counter_offer"]:
        co = notice_data["counter_offer"]
        counter_offer = CounterOffer(
            adjusted_term_months=co.get("adjusted_term_months", 0),
            adjusted_apr=co.get("adjusted_apr", 0),
            adjusted_monthly_payment=co.get("adjusted_monthly_payment", 0),
            required_down_payment=co.get("required_down_payment", 0)
        )

    notice = AdverseActionNotice(
        notice_id=notice_data.get("notice_id", ""),
        applicant_name=notice_data.get("applicant_name", ""),
        decision_date=notice_data.get("decision_date", ""),
        bureau_source=notice_data.get("bureau_source", ""),
        score_date=notice_data.get("score_date", ""),
        reasons=reasons,
        counter_offer=counter_offer
    )

    generator = get_pdf_generator()
    return generator.generate_adverse_action_notice(notice, language)


def generate_offering_price_pdf(
    vehicle_data: Dict[str, Any],
    components_data: Dict[str, Any],
    language: str = "en"
) -> BytesIO:
    """
    Convenience function to generate offering price PDF.

    Args:
        vehicle_data: Dictionary with vehicle data
        components_data: Dictionary with price components
        language: Language code

    Returns:
        BytesIO containing PDF content
    """
    vehicle = Vehicle(
        year=vehicle_data.get("year", 0),
        make=vehicle_data.get("make", ""),
        model=vehicle_data.get("model", ""),
        trim=vehicle_data.get("trim"),
        vin=vehicle_data.get("vin")
    )

    addons = [
        Addon(id=a.get("id", ""), name=a.get("name", ""), price=a.get("price", 0))
        for a in components_data.get("mandatory_addons", [])
    ]

    components = OfferingPriceComponents(
        base_vehicle_price=components_data.get("base_vehicle_price", 0),
        doc_fee=components_data.get("doc_fee", 0),
        mandatory_addons=addons,
        total_offering_price=components_data.get("total_offering_price", 0)
    )

    generator = get_pdf_generator()
    return generator.generate_offering_price_disclosure(vehicle, components, language)
