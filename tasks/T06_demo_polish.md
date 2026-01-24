# T06: Demo Polish (Frontend & UAT)

**Priority:** Lower
**Status:** Not Started
**Depends On:** T01, T02, T03, T04, T05 (All previous tasks)
**Blocked By:** T02, T03

---

## Objective

Polish the frontend UI and complete the demo-ready experience as specified in "The Trust Protocol" demo script. This includes interactive payment breakdown, PDF generation for adverse action notices, multi-language support, and pre-populated compliance logs for demo walkthroughs.

---

## Spec References

| Spec File | Section | Requirement |
|-----------|---------|-------------|
| `02_strategic_blueprint.md` | §1.3 The MVP Narrative: "The Trust Protocol" | 15-minute demo narrative |
| `02_strategic_blueprint.md` | §5 Demo Script | Scenes 1-4 with specific UI elements |
| `02_strategic_blueprint.md` | §5 Scene 1 | Inventory transparency with Offering Price table |
| `02_strategic_blueprint.md` | §5 Scene 2 | Soft-Pull Consent Card UI |
| `02_strategic_blueprint.md` | §5 Scene 3 | Interactive Payment Table with editable fields |
| `02_strategic_blueprint.md` | §5 Scene 4 | Adverse Action with PDF download link |
| `02_strategic_blueprint.md` | §4 User Story 11 | 3-Day Right to Cancel disclosure for CA used cars |
| `02_strategic_blueprint.md` | §4 User Story 12 | Multi-lingual disclosure (Spanish) |
| `03_implementation_dummy_data_plan.md` | §7 Synthetic Record Volume | 1,000 pre-filled compliance logs |
| `03_implementation_dummy_data_plan.md` | §6 Completeness Checklist | Demo UAT verification |

---

## Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/Deal/PaymentBreakdown.tsx` | Interactive deal structure table |
| `frontend/src/components/Deal/PaymentBreakdown.css` | Styling for payment table |
| `frontend/src/components/Common/OfferingPrice.tsx` | SB 766 compliant price display |
| `frontend/src/components/Common/OfferingPrice.css` | Styling for offering price |
| `frontend/src/components/Disclosure/CancellationOption.tsx` | CA 3-day cancel disclosure |
| `frontend/src/components/PDF/AdverseActionPDF.tsx` | PDF generation for denial notice |
| `frontend/src/i18n/en.json` | English language strings |
| `frontend/src/i18n/es.json` | Spanish language strings |
| `frontend/src/hooks/useLanguage.ts` | Language detection and switching |
| `backend/app/services/pdf_generator.py` | PDF generation service |
| `backend/app/routers/documents.py` | PDF download endpoint |
| `scripts/generate_demo_data.py` | Generate 1,000 compliance logs |
| `backend/tests/test_demo_scenarios.py` | End-to-end demo flow tests |

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/Chat/ChatPane.tsx` | Integrate new UI components |
| `frontend/src/components/Chat/MessageBubble.tsx` | Render rich cards (tables, PDFs) |
| `frontend/src/App.tsx` | Add language provider |
| `frontend/src/services/api.ts` | Add PDF download, language endpoints |
| `backend/app/main.py` | Register documents router |
| `scripts/seed_data.py` | Include demo compliance logs |

---

## Implementation Specifications

### PaymentBreakdown.tsx

Per Demo Script Scene 3:

```tsx
interface PaymentBreakdownProps {
  vehicle: Vehicle;
  customer: CustomerSummary;
  dealStructure: DealStructure;
  onDownPaymentChange: (amount: number) => void;
  onTermChange: (months: number) => void;
}

const PaymentBreakdown: React.FC<PaymentBreakdownProps> = ({
  vehicle,
  customer,
  dealStructure,
  onDownPaymentChange,
  onTermChange
}) => {
  return (
    <div className="payment-breakdown">
      <h3>Your Deal Structure</h3>

      <table className="deal-table">
        <tbody>
          <tr>
            <td>Price</td>
            <td className="amount">${dealStructure.sellingPrice.toLocaleString()}</td>
          </tr>
          <tr>
            <td>Taxes ({customer.jurisdiction})</td>
            <td className="amount">${dealStructure.taxCalculation.taxAmount.toLocaleString()}</td>
          </tr>
          <tr>
            <td>Registration</td>
            <td className="amount">${dealStructure.fees.registrationFee.toLocaleString()}</td>
          </tr>
          <tr>
            <td>Down Payment</td>
            <td>
              <input
                type="number"
                value={dealStructure.cashDownPayment}
                onChange={(e) => onDownPaymentChange(Number(e.target.value))}
                className="editable-field"
              />
            </td>
          </tr>
          <tr>
            <td>Term</td>
            <td>
              <select
                value={dealStructure.lendingTerms.termMonths}
                onChange={(e) => onTermChange(Number(e.target.value))}
                className="editable-field"
              >
                <option value={48}>48 Months</option>
                <option value={60}>60 Months</option>
                <option value={72}>72 Months</option>
              </select>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr className="total-row">
            <td>Monthly Payment</td>
            <td className="amount highlight">
              ${dealStructure.lendingTerms.monthlyPayment.toFixed(2)}
            </td>
          </tr>
        </tfoot>
      </table>

      <p className="apr-disclosure">
        APR: {dealStructure.lendingTerms.contractApr}% •
        Tier: {customer.creditTier}
      </p>
    </div>
  );
};
```

### OfferingPrice.tsx

Per Demo Script Scene 1 and SB 766:

```tsx
interface OfferingPriceProps {
  vehicle: Vehicle;
  components: OfferingPriceComponents;
}

const OfferingPrice: React.FC<OfferingPriceProps> = ({
  vehicle,
  components
}) => {
  return (
    <div className="offering-price sb766-compliant">
      <h3>Official Offering Price</h3>
      <p className="vehicle-title">
        {vehicle.year} {vehicle.make} {vehicle.model}
      </p>

      <table className="price-breakdown">
        <tbody>
          <tr>
            <td>Vehicle Price</td>
            <td>${components.baseVehiclePrice.toLocaleString()}</td>
          </tr>
          <tr>
            <td>Doc Fee</td>
            <td>${components.docFee.toLocaleString()}</td>
          </tr>
          {components.mandatoryAddons.map(addon => (
            <tr key={addon.id}>
              <td>{addon.name}</td>
              <td>${addon.price.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="total-row">
            <td><strong>Total Offering Price</strong></td>
            <td><strong>${components.totalOfferingPrice.toLocaleString()}</strong></td>
          </tr>
        </tfoot>
      </table>

      <p className="government-notice">
        Government taxes and registration fees are additional and
        calculated based on your location.
      </p>
    </div>
  );
};
```

### CancellationOption.tsx

Per User Story 11:

```tsx
interface CancellationOptionProps {
  vehicle: Vehicle;
  show: boolean;  // Only for CA used cars < $40k
}

const CancellationOption: React.FC<CancellationOptionProps> = ({
  vehicle,
  show
}) => {
  if (!show) return null;

  const optionCost = Math.min(vehicle.price * 0.01, 250);  // 1% or $250 max

  return (
    <div className="cancellation-disclosure">
      <h4>Your Right to Cancel</h4>
      <p>
        Under California law, you have the right to purchase a
        <strong> 2-Day Contract Cancellation Option</strong>.
      </p>
      <p>
        If purchased, you may cancel this contract within 2 days
        or 250 miles, whichever comes first.
      </p>
      <p className="option-cost">
        Cancellation Option Cost: <strong>${optionCost.toFixed(2)}</strong>
      </p>
    </div>
  );
};
```

### Multi-Language Support

**en.json:**
```json
{
  "offering_price": {
    "title": "Official Offering Price",
    "vehicle_price": "Vehicle Price",
    "doc_fee": "Doc Fee",
    "total": "Total Offering Price",
    "government_notice": "Government taxes and registration fees are additional."
  },
  "consent": {
    "title": "Credit Pre-Qualification",
    "text": "I understand that by clicking 'Submit', I am providing 'written instructions' under the FCRA authorizing {dealer} to obtain personal credit information...",
    "agree": "I Agree",
    "cancel": "Cancel"
  },
  "adverse_action": {
    "title": "Credit Decision",
    "reasons_title": "Principal Reasons for This Decision",
    "counter_offer": "Alternative Terms Available",
    "download_pdf": "Download Formal Notice (PDF)"
  }
}
```

**es.json:**
```json
{
  "offering_price": {
    "title": "Precio de Oferta Oficial",
    "vehicle_price": "Precio del Vehículo",
    "doc_fee": "Cargo por Documentación",
    "total": "Precio de Oferta Total",
    "government_notice": "Los impuestos gubernamentales y tarifas de registro son adicionales."
  },
  "consent": {
    "title": "Pre-Calificación de Crédito",
    "text": "Entiendo que al hacer clic en 'Enviar', estoy proporcionando 'instrucciones escritas' bajo la FCRA autorizando a {dealer} a obtener información crediticia personal...",
    "agree": "Acepto",
    "cancel": "Cancelar"
  },
  "adverse_action": {
    "title": "Decisión de Crédito",
    "reasons_title": "Razones Principales de Esta Decisión",
    "counter_offer": "Términos Alternativos Disponibles",
    "download_pdf": "Descargar Aviso Formal (PDF)"
  }
}
```

### pdf_generator.py

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO


class PDFGenerator:
    """
    Generate regulatory-compliant PDF documents.
    """

    def generate_adverse_action_notice(
        self,
        notice: AdverseActionNotice,
        language: str = "en"
    ) -> BytesIO:
        """
        Generate Regulation B compliant adverse action notice PDF.

        Includes:
        - Applicant name and date
        - Bureau source and score date
        - Up to 4 principal reasons with specific text
        - Counter-offer if applicable
        - Required regulatory footer
        """

    def generate_offering_price_disclosure(
        self,
        vehicle: Vehicle,
        components: OfferingPriceComponents,
        language: str = "en"
    ) -> BytesIO:
        """
        Generate SB 766 compliant offering price disclosure PDF.
        """
```

### generate_demo_data.py

```python
"""
Generate pre-filled demo data for UAT walkthroughs.

Per spec §7: 1,000 compliance logs for demo environment.
"""

def generate_compliance_logs(count: int = 1000):
    """
    Generate realistic compliance log entries.

    Distribution:
    - 60% successful disclosures (sb766_disclosure_verified: true)
    - 25% soft_pull_consent events
    - 10% adverse_action_generated
    - 5% disclosure_presented (other types)
    """

def generate_demo_customers(count: int = 100):
    """
    Generate demo customers with varied credit profiles.

    Distribution per spec §3.2.1:
    - 60% Prime (Score > 700)
    - 30% Subprime (Score < 620)
    - 10% Edge cases
    """

def generate_demo_deals(count: int = 50):
    """
    Generate demo deals in various states.

    - 20 working
    - 15 desked
    - 10 contracted
    - 5 funded
    """
```

---

## Demo Script Scene Alignment

### Scene 1: Inventory Transparency (0:00 - 4:00)

**Components Used:**
- `OfferingPrice.tsx` - Display SB 766 price breakdown
- Debugger panel shows agent reasoning

**Test:** `test_scene1_offering_price_displayed`

### Scene 2: Soft-Pull Handshake (4:00 - 8:00)

**Components Used:**
- `SoftPullCard.tsx` (from T03)
- Consent logging verified

**Test:** `test_scene2_consent_flow`

### Scene 3: Penny-Perfect Structuring (8:00 - 12:00)

**Components Used:**
- `PaymentBreakdown.tsx` - Interactive table
- Down payment and term editable
- Real-time recalculation

**Test:** `test_scene3_interactive_payment`

### Scene 4: Adverse Action (12:00 - 15:00)

**Components Used:**
- Adverse action message with specific reasons
- `AdverseActionPDF.tsx` - PDF download link
- Counter-offer display

**Test:** `test_scene4_adverse_action_pdf`

---

## Acceptance Tests

### Test File: `backend/tests/test_demo_scenarios.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T06-01 | `test_scene1_offering_price_before_payment` | Payment inquiry triggers offering price first |
| T06-02 | `test_scene1_offering_price_format` | Response includes itemized SB 766 table |
| T06-03 | `test_scene2_consent_card_rendered` | "Can I get approved?" triggers consent UI |
| T06-04 | `test_scene2_consent_logged_fcra` | Consent creates FCRA-compliant log entry |
| T06-05 | `test_scene3_payment_interactive` | Payment response includes editable fields |
| T06-06 | `test_scene3_recalculation` | Changing down payment updates monthly |
| T06-07 | `test_scene4_adverse_specific_reasons` | Decline includes Reg B reason codes |
| T06-08 | `test_scene4_pdf_download` | PDF endpoint returns valid PDF |
| T06-09 | `test_scene4_counter_offer` | Conditional decline includes counter-offer |

### Test File: `frontend/src/__tests__/components.test.tsx`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T06-10 | `test_offering_price_renders` | OfferingPrice component renders all fields |
| T06-11 | `test_payment_breakdown_editable` | Input fields are editable |
| T06-12 | `test_cancellation_shows_ca_used` | CancellationOption shows for CA used car < $40k |
| T06-13 | `test_cancellation_hidden_new` | CancellationOption hidden for new cars |
| T06-14 | `test_language_switch_spanish` | Components render in Spanish when selected |

### Test File: `backend/tests/test_pdf_generation.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T06-15 | `test_adverse_action_pdf_valid` | Generated PDF opens without error |
| T06-16 | `test_adverse_action_pdf_reasons` | PDF contains all reason codes |
| T06-17 | `test_adverse_action_pdf_spanish` | Spanish PDF uses translated text |
| T06-18 | `test_offering_price_pdf_valid` | Generated disclosure PDF valid |

### Test File: `backend/tests/test_demo_data.py`

| Test ID | Test Name | Assertion |
|---------|-----------|-----------|
| T06-19 | `test_compliance_logs_generated` | 1,000 compliance logs exist |
| T06-20 | `test_demo_customers_distribution` | 60% prime, 30% subprime, 10% edge |
| T06-21 | `test_demo_deals_varied_status` | Deals in all status states |

---

## UAT Completeness Checklist

Per `03_implementation_dummy_data_plan.md` §6:

### Financial Completeness
| Check | Test |
|-------|------|
| Penny-Perfect Verification: $35k/5%/60mo = $660.49 | T04-16 |
| Negative Equity Handling | T04-17 |
| Payment Packing Prevention | T04-18, T04-19 |

### Regulatory Completeness (SB 766 / CARS / FCRA)
| Check | Test |
|-------|------|
| Offering Price stored statically | T02-03 |
| Benefit Statement Validation | T02-05, T02-06 |
| Consent Logging with IP/Timestamp | T03-09, T03-10 |
| Cancellation Option for CA used < $40k | T06-12, T06-13 |

### Governance Completeness
| Check | Test |
|-------|------|
| Cross-Store Isolation | T05-04 |
| Manager Override | T05-02 |
| Audit Trail Fidelity | T05-26 |
| Agent PII Restriction | T05-27 |

---

## Definition of Done

- [ ] `PaymentBreakdown.tsx` with interactive editable fields
- [ ] `OfferingPrice.tsx` with SB 766 compliant format
- [ ] `CancellationOption.tsx` for CA used cars
- [ ] Multi-language support (en/es) implemented
- [ ] PDF generation for adverse action notices
- [ ] 1,000 demo compliance logs generated
- [ ] 100 demo customers with varied profiles
- [ ] 50 demo deals in various states
- [ ] All 21 acceptance tests pass
- [ ] Full 15-minute demo script executable end-to-end
- [ ] UAT completeness checklist verified
- [ ] No regressions in existing tests
