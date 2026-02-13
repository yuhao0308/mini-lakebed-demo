import React from 'react'
import { Receipt, Info } from 'lucide-react'
import './OfferingPrice.css'

interface Addon {
    id: string
    name: string
    price: number
}

interface OfferingPriceComponents {
    baseVehiclePrice: number
    docFee: number
    mandatoryAddons: Addon[]
    totalOfferingPrice: number
}

interface Vehicle {
    year: number
    make: string
    model: string
    trim?: string
    vin?: string
}

interface OfferingPriceProps {
    vehicle: Vehicle
    components: OfferingPriceComponents
}

const OfferingPrice: React.FC<OfferingPriceProps> = ({
    vehicle,
    components
}) => {
    return (
        <div className="offering-price sb766-compliant">
            <div className="offering-header">
                <Receipt size={20} className="icon" />
                <h3>Official Offering Price</h3>
            </div>

            <p className="vehicle-title">
                {vehicle.year} {vehicle.make} {vehicle.model} {vehicle.trim && `${vehicle.trim}`}
            </p>

            <table className="price-breakdown">
                <tbody>
                    <tr>
                        <td>Vehicle Price</td>
                        <td className="amount">${components.baseVehiclePrice.toLocaleString()}</td>
                    </tr>
                    <tr>
                        <td>Doc Fee</td>
                        <td className="amount">${components.docFee.toLocaleString()}</td>
                    </tr>
                    {components.mandatoryAddons.map(addon => (
                        <tr key={addon.id}>
                            <td>{addon.name}</td>
                            <td className="amount">${addon.price.toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className="total-row">
                        <td><strong>Total Offering Price</strong></td>
                        <td className="amount"><strong>${components.totalOfferingPrice.toLocaleString()}</strong></td>
                    </tr>
                </tfoot>
            </table>

            <div className="government-notice">
                <Info size={14} />
                <p>
                    Government taxes and registration fees are additional and
                    calculated based on your location.
                </p>
            </div>

            <div className="sb766-badge">
                <span>SB 766 Compliant</span>
            </div>
        </div>
    )
}

export default OfferingPrice
