import React from 'react'
import { Calculator, ShieldCheck } from 'lucide-react'
import './PaymentBreakdown.css'

interface TaxCalculation {
    taxAmount: number
    taxRate: number
    jurisdiction: string
}

interface Fees {
    registrationFee: number
    docFee: number
    totalFees: number
}

interface LendingTerms {
    termMonths: number
    contractApr: number
    monthlyPayment: number
    amountFinanced: number
    totalOfPayments: number
    financeCharge: number
}

interface DealStructure {
    sellingPrice: number
    taxCalculation: TaxCalculation
    fees: Fees
    cashDownPayment: number
    lendingTerms: LendingTerms
}

interface CustomerSummary {
    creditTier: string
    jurisdiction: string
}

interface Vehicle {
    year: number
    make: string
    model: string
    price: number
}

interface PaymentBreakdownProps {
    vehicle: Vehicle
    customer: CustomerSummary
    dealStructure: DealStructure
    onDownPaymentChange?: (amount: number) => void
    onTermChange?: (months: number) => void
    editable?: boolean
}

const PaymentBreakdown: React.FC<PaymentBreakdownProps> = ({
    vehicle,
    customer,
    dealStructure,
    onDownPaymentChange,
    onTermChange,
    editable = true
}) => {
    const handleDownPaymentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (onDownPaymentChange) {
            onDownPaymentChange(Number(e.target.value))
        }
    }

    const handleTermChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        if (onTermChange) {
            onTermChange(Number(e.target.value))
        }
    }

    return (
        <div className="payment-breakdown">
            <div className="breakdown-header">
                <Calculator size={20} className="icon" />
                <h3>Your Deal Structure</h3>
            </div>

            <p className="vehicle-title">
                {vehicle.year} {vehicle.make} {vehicle.model}
            </p>

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
                            {editable ? (
                                <input
                                    type="number"
                                    value={dealStructure.cashDownPayment}
                                    onChange={handleDownPaymentChange}
                                    className="editable-field"
                                    min={0}
                                    step={500}
                                />
                            ) : (
                                <span className="amount">${dealStructure.cashDownPayment.toLocaleString()}</span>
                            )}
                        </td>
                    </tr>
                    <tr>
                        <td>Term</td>
                        <td>
                            {editable ? (
                                <select
                                    value={dealStructure.lendingTerms.termMonths}
                                    onChange={handleTermChange}
                                    className="editable-field"
                                >
                                    <option value={48}>48 Months</option>
                                    <option value={60}>60 Months</option>
                                    <option value={72}>72 Months</option>
                                </select>
                            ) : (
                                <span className="amount">{dealStructure.lendingTerms.termMonths} Months</span>
                            )}
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
                APR: {dealStructure.lendingTerms.contractApr}% | Tier: {customer.creditTier}
            </p>

            <div className="finance-details">
                <span>Amount Financed: ${dealStructure.lendingTerms.amountFinanced.toLocaleString()}</span>
                <span>Finance Charge: ${dealStructure.lendingTerms.financeCharge.toLocaleString()}</span>
                <span>Total of Payments: ${dealStructure.lendingTerms.totalOfPayments.toLocaleString()}</span>
            </div>

            <div className="disclaimer-mini">
                <ShieldCheck size={12} />
                <span>DEMO ONLY: Synthetic rules. Not a commitment to lend.</span>
            </div>
        </div>
    )
}

export default PaymentBreakdown
