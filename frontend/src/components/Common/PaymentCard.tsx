import React from 'react'
import { Calculator, Info, ShieldCheck } from 'lucide-react'
import type { PaymentEstimate } from '../../types'
import './PaymentCard.css'

interface PaymentCardProps {
    estimate: PaymentEstimate
    ruleId?: string
    calculationTrace?: any
}

const PaymentCard: React.FC<PaymentCardProps> = ({ estimate, ruleId, calculationTrace: _calculationTrace }) => {
    return (
        <div className="payment-card">
            <div className="card-header">
                <Calculator size={20} className="icon" />
                <span className="title">Payment Estimate</span>
            </div>

            <div className="main-stat">
                <span className="currency">$</span>
                <span className="amount">{estimate.monthly_payment.toFixed(2)}</span>
                <span className="period">/mo</span>
            </div>

            <div className="stats-grid">
                <div className="stat">
                    <span className="label">APR</span>
                    <span className="value">{estimate.apr}%</span>
                </div>
                <div className="stat">
                    <span className="label">TERM</span>
                    <span className="value">{estimate.term_months} mo</span>
                </div>
                <div className="stat">
                    <span className="label">PRINCIPAL</span>
                    <span className="value">${estimate.principal.toLocaleString()}</span>
                </div>
            </div>

            {ruleId && (
                <div className="rule-citation">
                    <Info size={14} />
                    <span>Rule ID: {ruleId}</span>
                </div>
            )}

            <div className="disclaimer-mini">
                <ShieldCheck size={12} />
                <span>DEMO ONLY: Synthetic rules. Not a commitment to lend.</span>
            </div>
        </div>
    )
}

export default PaymentCard
