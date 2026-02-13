"""
T06: Documents Router

PDF download endpoints for adverse action notices and disclosures.

Per tasks/T06_demo_polish.md
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.services.pdf_generator import (
    generate_adverse_action_pdf,
    generate_offering_price_pdf
)

router = APIRouter(prefix="/documents", tags=["Documents"])


class ReasonRequest(BaseModel):
    """Adverse action reason."""
    code: str
    text: str


class CounterOfferRequest(BaseModel):
    """Counter-offer for conditional decline."""
    adjusted_term_months: int
    adjusted_apr: float
    adjusted_monthly_payment: float
    required_down_payment: float


class AdverseActionRequest(BaseModel):
    """Request to generate adverse action PDF."""
    notice_id: str
    applicant_name: str
    decision_date: str
    bureau_source: str
    score_date: str
    reasons: List[ReasonRequest]
    counter_offer: Optional[CounterOfferRequest] = None
    language: str = "en"


class AddonRequest(BaseModel):
    """Vehicle addon."""
    id: str
    name: str
    price: float


class VehicleRequest(BaseModel):
    """Vehicle information."""
    year: int
    make: str
    model: str
    trim: Optional[str] = None
    vin: Optional[str] = None


class OfferingPriceComponentsRequest(BaseModel):
    """Offering price components."""
    base_vehicle_price: float
    doc_fee: float
    mandatory_addons: List[AddonRequest] = []
    total_offering_price: float


class OfferingPriceRequest(BaseModel):
    """Request to generate offering price PDF."""
    vehicle: VehicleRequest
    components: OfferingPriceComponentsRequest
    language: str = "en"


@router.post("/adverse-action/pdf")
async def download_adverse_action_pdf(request: AdverseActionRequest):
    """
    Generate and download adverse action notice PDF.

    Per Demo Script Scene 4 and Regulation B compliance.

    Args:
        request: AdverseActionRequest with notice data

    Returns:
        PDF file as streaming response
    """
    try:
        # Convert request to dict for PDF generator
        notice_data = {
            "notice_id": request.notice_id,
            "applicant_name": request.applicant_name,
            "decision_date": request.decision_date,
            "bureau_source": request.bureau_source,
            "score_date": request.score_date,
            "reasons": [{"code": r.code, "text": r.text} for r in request.reasons]
        }

        if request.counter_offer:
            notice_data["counter_offer"] = {
                "adjusted_term_months": request.counter_offer.adjusted_term_months,
                "adjusted_apr": request.counter_offer.adjusted_apr,
                "adjusted_monthly_payment": request.counter_offer.adjusted_monthly_payment,
                "required_down_payment": request.counter_offer.required_down_payment
            }

        pdf_buffer = generate_adverse_action_pdf(notice_data, request.language)

        filename = f"adverse_action_{request.notice_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/offering-price/pdf")
async def download_offering_price_pdf(request: OfferingPriceRequest):
    """
    Generate and download SB 766 offering price disclosure PDF.

    Per Demo Script Scene 1 and SB 766 compliance.

    Args:
        request: OfferingPriceRequest with vehicle and price data

    Returns:
        PDF file as streaming response
    """
    try:
        vehicle_data = {
            "year": request.vehicle.year,
            "make": request.vehicle.make,
            "model": request.vehicle.model,
            "trim": request.vehicle.trim,
            "vin": request.vehicle.vin
        }

        components_data = {
            "base_vehicle_price": request.components.base_vehicle_price,
            "doc_fee": request.components.doc_fee,
            "mandatory_addons": [
                {"id": a.id, "name": a.name, "price": a.price}
                for a in request.components.mandatory_addons
            ],
            "total_offering_price": request.components.total_offering_price
        }

        pdf_buffer = generate_offering_price_pdf(vehicle_data, components_data, request.language)

        filename = f"offering_price_{request.vehicle.year}_{request.vehicle.make}_{request.vehicle.model}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filename = filename.replace(" ", "_")

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/adverse-action/sample")
async def get_sample_adverse_action(language: str = Query("en", pattern="^(en|es)$")):
    """
    Generate a sample adverse action PDF for demo purposes.

    Returns:
        PDF file as streaming response
    """
    sample_notice = {
        "notice_id": "DEMO-AA-001",
        "applicant_name": "Demo Customer",
        "decision_date": datetime.now().strftime("%Y-%m-%d"),
        "bureau_source": "Experian",
        "score_date": datetime.now().strftime("%Y-%m-%d"),
        "reasons": [
            {"code": "A01", "text": "Too many inquiries in the last 12 months"},
            {"code": "B02", "text": "Amount owed on revolving accounts is too high"},
            {"code": "C03", "text": "Proportion of balances to credit limits is too high"},
            {"code": "D04", "text": "Length of time accounts have been established"}
        ],
        "counter_offer": {
            "adjusted_term_months": 48,
            "adjusted_apr": 12.99,
            "adjusted_monthly_payment": 785.50,
            "required_down_payment": 5000.00
        }
    }

    pdf_buffer = generate_adverse_action_pdf(sample_notice, language)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=sample_adverse_action_{language}.pdf"
        }
    )


@router.get("/offering-price/sample")
async def get_sample_offering_price(language: str = Query("en", pattern="^(en|es)$")):
    """
    Generate a sample offering price PDF for demo purposes.

    Returns:
        PDF file as streaming response
    """
    sample_vehicle = {
        "year": 2024,
        "make": "Toyota",
        "model": "Camry",
        "trim": "LE",
        "vin": "4T1BF1FK5EU123456"
    }

    sample_components = {
        "base_vehicle_price": 28995.00,
        "doc_fee": 85.00,
        "mandatory_addons": [
            {"id": "addon_1", "name": "Nitrogen Tire Fill", "price": 199.00},
            {"id": "addon_2", "name": "All-Weather Floor Mats", "price": 249.00}
        ],
        "total_offering_price": 29528.00
    }

    pdf_buffer = generate_offering_price_pdf(sample_vehicle, sample_components, language)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=sample_offering_price_{language}.pdf"
        }
    )
