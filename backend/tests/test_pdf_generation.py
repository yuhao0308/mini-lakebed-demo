"""
T06: PDF Generation Tests

Tests for PDF generator service.
Per tasks/T06_demo_polish.md acceptance tests T06-15 through T06-18.
"""

import pytest
from io import BytesIO

from app.services.pdf_generator import (
    PDFGenerator,
    AdverseActionNotice,
    OfferingPriceComponents,
    Vehicle,
    Reason,
    CounterOffer,
    Addon,
    get_pdf_generator,
    generate_adverse_action_pdf,
    generate_offering_price_pdf
)


class TestPDFGenerator:
    """Tests for PDFGenerator class."""

    @pytest.fixture
    def generator(self) -> PDFGenerator:
        """Get PDF generator instance."""
        return get_pdf_generator()

    @pytest.fixture
    def sample_notice(self) -> AdverseActionNotice:
        """Create sample adverse action notice."""
        return AdverseActionNotice(
            notice_id="TEST-001",
            applicant_name="John Doe",
            decision_date="2026-01-25",
            bureau_source="Experian",
            score_date="2026-01-24",
            reasons=[
                Reason(code="A01", text="Too many inquiries in the last 12 months"),
                Reason(code="B02", text="Amount owed on revolving accounts is too high"),
                Reason(code="C03", text="Too few bank revolving accounts"),
                Reason(code="D04", text="Too many bank accounts with balances")
            ]
        )

    @pytest.fixture
    def sample_vehicle(self) -> Vehicle:
        """Create sample vehicle."""
        return Vehicle(
            year=2024,
            make="Toyota",
            model="Camry",
            trim="LE",
            vin="4T1BF1FK5EU123456"
        )

    @pytest.fixture
    def sample_components(self) -> OfferingPriceComponents:
        """Create sample offering price components."""
        return OfferingPriceComponents(
            base_vehicle_price=28995.00,
            doc_fee=85.00,
            mandatory_addons=[
                Addon(id="addon_1", name="Floor Mats", price=199.00)
            ],
            total_offering_price=29279.00
        )

    # T06-15: test_adverse_action_pdf_valid
    def test_adverse_action_pdf_valid(
        self,
        generator: PDFGenerator,
        sample_notice: AdverseActionNotice
    ):
        """
        T06-15: Generated PDF opens without error.

        PDF should be valid and contain required markers.
        """
        pdf_buffer = generator.generate_adverse_action_notice(sample_notice)

        assert isinstance(pdf_buffer, BytesIO)
        content = pdf_buffer.getvalue()

        # Should start with PDF header
        assert content.startswith(b"%PDF")

        # Should end with PDF footer
        assert b"%%EOF" in content

    # T06-16: test_adverse_action_pdf_reasons
    def test_adverse_action_pdf_reasons(
        self,
        generator: PDFGenerator,
        sample_notice: AdverseActionNotice
    ):
        """
        T06-16: PDF contains all reason codes.

        All provided reason codes should appear in PDF content.
        """
        pdf_buffer = generator.generate_adverse_action_notice(sample_notice)
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        # Check all reason codes are present
        assert "A01" in content
        assert "B02" in content
        assert "C03" in content
        assert "D04" in content

        # Check reason text is present
        assert "inquiries" in content.lower()
        assert "revolving" in content.lower()

    # T06-17: test_adverse_action_pdf_spanish
    def test_adverse_action_pdf_spanish(
        self,
        generator: PDFGenerator,
        sample_notice: AdverseActionNotice
    ):
        """
        T06-17: Spanish PDF uses translated text.

        Spanish version should contain Spanish text.
        """
        pdf_buffer = generator.generate_adverse_action_notice(sample_notice, language="es")
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        # Check Spanish title
        assert "ACCIÓN ADVERSA" in content or "ADVERSA" in content

        # Check Spanish text elements
        assert "Solicitante" in content or "Decisión" in content

    # T06-18: test_offering_price_pdf_valid
    def test_offering_price_pdf_valid(
        self,
        generator: PDFGenerator,
        sample_vehicle: Vehicle,
        sample_components: OfferingPriceComponents
    ):
        """
        T06-18: Generated disclosure PDF valid.

        PDF should be valid and contain required information.
        """
        pdf_buffer = generator.generate_offering_price_disclosure(
            sample_vehicle,
            sample_components
        )

        assert isinstance(pdf_buffer, BytesIO)
        content = pdf_buffer.getvalue()

        # Should start with PDF header
        assert content.startswith(b"%PDF")

        # Check content
        text_content = content.decode('utf-8', errors='ignore')
        assert "Toyota" in text_content
        assert "Camry" in text_content
        assert "SB 766" in text_content


class TestPDFContent:
    """Tests for PDF content generation."""

    @pytest.fixture
    def generator(self) -> PDFGenerator:
        """Get PDF generator instance."""
        return PDFGenerator()

    def test_adverse_action_contains_applicant_info(self, generator: PDFGenerator):
        """Test that applicant info is included."""
        notice = AdverseActionNotice(
            notice_id="TEST-002",
            applicant_name="Jane Smith",
            decision_date="2026-01-25",
            bureau_source="TransUnion",
            score_date="2026-01-24",
            reasons=[Reason(code="A01", text="Test reason")]
        )

        pdf_buffer = generator.generate_adverse_action_notice(notice)
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        assert "Jane Smith" in content
        assert "TransUnion" in content
        assert "TEST-002" in content

    def test_adverse_action_with_counter_offer(self, generator: PDFGenerator):
        """Test that counter-offer is included when present."""
        notice = AdverseActionNotice(
            notice_id="TEST-003",
            applicant_name="Test User",
            decision_date="2026-01-25",
            bureau_source="Equifax",
            score_date="2026-01-24",
            reasons=[Reason(code="B02", text="Test reason")],
            counter_offer=CounterOffer(
                adjusted_term_months=48,
                adjusted_apr=12.99,
                adjusted_monthly_payment=785.50,
                required_down_payment=5000.00
            )
        )

        pdf_buffer = generator.generate_adverse_action_notice(notice)
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        assert "48" in content
        assert "12.99" in content
        assert "785.50" in content
        assert "5,000" in content or "5000" in content

    def test_offering_price_contains_breakdown(self, generator: PDFGenerator):
        """Test that price breakdown is included."""
        vehicle = Vehicle(year=2024, make="Honda", model="Accord")
        components = OfferingPriceComponents(
            base_vehicle_price=32000.00,
            doc_fee=100.00,
            mandatory_addons=[
                Addon(id="1", name="Window Tint", price=300.00),
                Addon(id="2", name="Paint Protection", price=500.00)
            ],
            total_offering_price=32900.00
        )

        pdf_buffer = generator.generate_offering_price_disclosure(vehicle, components)
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        assert "Honda" in content
        assert "Accord" in content
        assert "32,000" in content or "32000" in content
        assert "Window Tint" in content
        assert "Paint Protection" in content

    def test_offering_price_spanish(self, generator: PDFGenerator):
        """Test Spanish offering price PDF."""
        vehicle = Vehicle(year=2024, make="Ford", model="F-150")
        components = OfferingPriceComponents(
            base_vehicle_price=45000.00,
            doc_fee=85.00,
            mandatory_addons=[],
            total_offering_price=45085.00
        )

        pdf_buffer = generator.generate_offering_price_disclosure(
            vehicle, components, language="es"
        )
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        assert "PRECIO" in content or "Precio" in content
        assert "SB 766" in content


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_adverse_action_pdf_function(self):
        """Test generate_adverse_action_pdf function."""
        notice_data = {
            "notice_id": "FUNC-TEST-001",
            "applicant_name": "Function Test",
            "decision_date": "2026-01-25",
            "bureau_source": "Experian",
            "score_date": "2026-01-24",
            "reasons": [
                {"code": "A01", "text": "Test reason 1"},
                {"code": "B02", "text": "Test reason 2"}
            ]
        }

        pdf_buffer = generate_adverse_action_pdf(notice_data)

        assert isinstance(pdf_buffer, BytesIO)
        content = pdf_buffer.getvalue()
        assert content.startswith(b"%PDF")

    def test_generate_offering_price_pdf_function(self):
        """Test generate_offering_price_pdf function."""
        vehicle_data = {
            "year": 2024,
            "make": "Chevrolet",
            "model": "Tahoe"
        }
        components_data = {
            "base_vehicle_price": 55000.00,
            "doc_fee": 85.00,
            "mandatory_addons": [],
            "total_offering_price": 55085.00
        }

        pdf_buffer = generate_offering_price_pdf(vehicle_data, components_data)

        assert isinstance(pdf_buffer, BytesIO)
        content = pdf_buffer.getvalue()
        assert content.startswith(b"%PDF")

    def test_get_pdf_generator_singleton(self):
        """Test that get_pdf_generator returns singleton."""
        gen1 = get_pdf_generator()
        gen2 = get_pdf_generator()

        assert gen1 is gen2


class TestMaxReasons:
    """Tests for maximum reasons handling."""

    def test_max_4_reasons(self):
        """Test that only max 4 reasons are included per Reg B."""
        generator = PDFGenerator()
        notice = AdverseActionNotice(
            notice_id="TEST-MAX",
            applicant_name="Max Test",
            decision_date="2026-01-25",
            bureau_source="Experian",
            score_date="2026-01-24",
            reasons=[
                Reason(code="A01", text="Reason 1"),
                Reason(code="A02", text="Reason 2"),
                Reason(code="A03", text="Reason 3"),
                Reason(code="A04", text="Reason 4"),
                Reason(code="A05", text="Reason 5"),  # Should not appear
                Reason(code="A06", text="Reason 6")   # Should not appear
            ]
        )

        pdf_buffer = generator.generate_adverse_action_notice(notice)
        content = pdf_buffer.getvalue().decode('utf-8', errors='ignore')

        # First 4 should appear
        assert "A01" in content
        assert "A02" in content
        assert "A03" in content
        assert "A04" in content

        # 5th and 6th should not appear (per Reg B max 4)
        assert "A05" not in content
        assert "A06" not in content
