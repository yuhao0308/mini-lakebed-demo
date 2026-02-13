import React from 'react'
import { AlertCircle, FileText } from 'lucide-react'
import './CancellationOption.css'

interface Vehicle {
    year: number
    make: string
    model: string
    price: number
    isNew?: boolean
}

interface CancellationOptionProps {
    vehicle: Vehicle
    show: boolean  // Only for CA used cars < $40k
    customerState?: string
}

/**
 * CancellationOption - CA 3-Day Contract Cancellation Option Disclosure
 *
 * Per User Story 11 and California law:
 * - Only applies to used cars under $40,000
 * - Cost is 1% of price or $250, whichever is less
 * - Allows cancellation within 2 days or 250 miles
 */
const CancellationOption: React.FC<CancellationOptionProps> = ({
    vehicle,
    show,
    customerState = 'CA'
}) => {
    // Only show for CA used cars under $40k
    if (!show) return null

    // Don't show for new cars
    if (vehicle.isNew) return null

    // Don't show for vehicles over $40k
    if (vehicle.price >= 40000) return null

    // Only show for California
    if (customerState !== 'CA') return null

    // Calculate option cost: 1% of price or $250, whichever is less
    const optionCost = Math.min(vehicle.price * 0.01, 250)

    return (
        <div className="cancellation-disclosure">
            <div className="disclosure-header">
                <AlertCircle size={20} className="icon" />
                <h4>Your Right to Cancel</h4>
            </div>

            <div className="disclosure-content">
                <p>
                    Under California law, you have the right to purchase a
                    <strong> 2-Day Contract Cancellation Option</strong>.
                </p>

                <p>
                    If purchased, you may cancel this contract within <strong>2 days</strong>{' '}
                    or <strong>250 miles</strong>, whichever comes first.
                </p>

                <div className="option-cost">
                    <FileText size={16} />
                    <span>Cancellation Option Cost: <strong>${optionCost.toFixed(2)}</strong></span>
                </div>
            </div>

            <div className="legal-notice">
                <p>
                    This disclosure is required under California Vehicle Code Section 11709.2.
                    The purchase of this option is voluntary.
                </p>
            </div>
        </div>
    )
}

export default CancellationOption
