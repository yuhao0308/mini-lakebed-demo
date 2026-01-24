import React from 'react'
import { Car, Tag, Activity, ArrowRight } from 'lucide-react'
import type { Vehicle } from '../../types'
import './InventoryCard.css'

interface InventoryCardProps {
    vehicle: Vehicle
    onClick?: () => void
}

const InventoryCard: React.FC<InventoryCardProps> = ({ vehicle, onClick }) => {
    return (
        <div className="inventory-card" onClick={onClick}>
            <div className="card-top">
                <div className="vehicle-icon">
                    <Car size={20} />
                </div>
                <div className="price-tag">
                    ${vehicle.price.toLocaleString()}
                </div>
            </div>

            <div className="card-main">
                <h4 className="vehicle-title">{vehicle.year} {vehicle.make} {vehicle.model}</h4>
                <div className="vehicle-stats">
                    <div className="stat-item">
                        <Tag size={12} />
                        <span>{vehicle.body_style}</span>
                    </div>
                    <div className="stat-item">
                        <Activity size={12} />
                        <span>{vehicle.mileage.toLocaleString()} mi</span>
                    </div>
                </div>
            </div>

            <div className="card-footer">
                <span className={`status-pill ${vehicle.status}`}>
                    {vehicle.status}
                </span>
                <button className="view-details-btn">
                    Details <ArrowRight size={14} />
                </button>
            </div>
        </div>
    )
}

export default InventoryCard
