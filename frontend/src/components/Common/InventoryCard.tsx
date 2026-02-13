import React from 'react'
import { Car, Tag, Activity, ExternalLink, Hash, Fingerprint, Plus, Check } from 'lucide-react'
import type { Vehicle } from '../../types'
import './InventoryCard.css'

interface InventoryCardProps {
    vehicle: Vehicle
    isFlipped: boolean
    onToggleFlip: () => void
    onRequestDetails?: (vehicle: Vehicle, position?: number) => void
    onToggleComposerSelection?: (vehicle: Vehicle) => void
    isComposerSelected?: boolean
    actionsDisabled?: boolean
    index?: number
}

const InventoryCard: React.FC<InventoryCardProps> = ({
    vehicle,
    isFlipped,
    onToggleFlip,
    onRequestDetails,
    onToggleComposerSelection,
    isComposerSelected = false,
    actionsDisabled = false,
    index
}) => {
    const displayName = `${vehicle.year} ${vehicle.make} ${vehicle.model}`
    const trimName = vehicle.trim && vehicle.trim.trim().length > 0 ? vehicle.trim : 'Standard trim'
    const statusClass = vehicle.status.toLowerCase()
    const vinLast = vehicle.vin ? vehicle.vin.slice(-8).toUpperCase() : 'N/A'
    const detailPosition = index !== undefined ? index + 1 : undefined

    const handleRequestDetails = () => {
        onRequestDetails?.(vehicle, detailPosition)
    }

    const handleFullDetailsClick = (event: React.MouseEvent<HTMLButtonElement>) => {
        event.stopPropagation()
        handleRequestDetails()
    }

    const handleAddToMessageClick = (event: React.MouseEvent<HTMLButtonElement>) => {
        event.stopPropagation()
        onToggleComposerSelection?.(vehicle)
    }

    return (
        <div
            className={`inventory-card ${isFlipped ? 'is-flipped' : ''}`}
            data-testid={`inventory-card${index !== undefined ? `-${index}` : ''}`}
        >
            <div className="inventory-card-inner">
                <div className="inventory-card-face inventory-card-front">
                    <div className="card-shell">
                        <div className="card-top">
                            <div className="vehicle-icon">
                                <Car size={18} />
                            </div>
                            <div className="price-tag">
                                ${vehicle.price.toLocaleString()}
                            </div>
                        </div>

                        <div className="card-main">
                            <h4 className="vehicle-title" data-testid="vehicle-title">{displayName}</h4>
                            <div className="vehicle-trim">{trimName}</div>
                            <div className="vehicle-stats">
                                <div className="stat-item" data-testid="vehicle-body-style">
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
                            <span className={`status-pill ${statusClass}`}>
                                {vehicle.status}
                            </span>
                            <div className="card-actions-group">
                                <button
                                    type="button"
                                    className={`card-action-btn composer-toggle ${isComposerSelected ? 'active' : ''}`}
                                    onClick={handleAddToMessageClick}
                                    disabled={actionsDisabled}
                                    aria-pressed={isComposerSelected}
                                >
                                    {isComposerSelected ? <Check size={13} /> : <Plus size={13} />}
                                    {isComposerSelected ? 'Added' : 'Add to message'}
                                </button>
                                <button
                                    type="button"
                                    className="card-action-btn primary"
                                    onClick={onToggleFlip}
                                    disabled={actionsDisabled}
                                >
                                    Details
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="inventory-card-face inventory-card-back" onClick={onToggleFlip}>
                    <div className="card-shell">
                        <div className="card-back-header">
                            <div className="card-back-title">Quick Vehicle View</div>
                            <span className={`status-pill ${statusClass}`}>
                                {vehicle.status}
                            </span>
                        </div>

                        <div className="card-detail-grid">
                            <div className="detail-row">
                                <span className="detail-label"><Hash size={12} /> Stock</span>
                                <span className="detail-value">{vehicle.id}</span>
                            </div>
                            <div className="detail-row">
                                <span className="detail-label"><Tag size={12} /> Body</span>
                                <span className="detail-value">{vehicle.body_style}</span>
                            </div>
                            <div className="detail-row">
                                <span className="detail-label"><Activity size={12} /> Mileage</span>
                                <span className="detail-value">{vehicle.mileage.toLocaleString()} mi</span>
                            </div>
                            <div className="detail-row">
                                <span className="detail-label"><Fingerprint size={12} /> VIN</span>
                                <span className="detail-value">...{vinLast}</span>
                            </div>
                        </div>

                        <div className="card-back-note">
                            Ready for a full assistant breakdown and next-step actions.
                        </div>

                        <div className="card-footer dual-actions">
                            <button
                                type="button"
                                className={`card-action-btn composer-toggle ${isComposerSelected ? 'active' : ''}`}
                                onClick={handleAddToMessageClick}
                                disabled={actionsDisabled}
                                aria-pressed={isComposerSelected}
                            >
                                {isComposerSelected ? <Check size={13} /> : <Plus size={13} />}
                                {isComposerSelected ? 'Added' : 'Add to message'}
                            </button>
                            <button
                                type="button"
                                className="card-action-btn primary"
                                onClick={handleFullDetailsClick}
                                disabled={actionsDisabled}
                            >
                                <ExternalLink size={13} />
                                Full details in chat
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default InventoryCard
