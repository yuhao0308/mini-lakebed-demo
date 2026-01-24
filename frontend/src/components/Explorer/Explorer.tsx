import React, { useState, useEffect } from 'react'
import { ChevronRight, Database, Folder, FileText, Plus, Search, Filter } from 'lucide-react'
import { apiService } from '../../services/api'
import type { Lake, Zone, Asset } from '../../types'
import './Explorer.css'

const Explorer: React.FC = () => {
    const [lakes, setLakes] = useState<Lake[]>([])
    const [selectedLake, setSelectedLake] = useState<string | null>(null)
    const [zones, setZones] = useState<Zone[]>([])
    const [selectedZone, setSelectedZone] = useState<string | null>(null)
    const [assets, setAssets] = useState<Asset[]>([])

    useEffect(() => {
        loadLakes()
    }, [])

    const loadLakes = async () => {
        const data = await apiService.getLakes()
        setLakes(data)
    }

    const handleLakeClick = async (lakeId: string) => {
        setSelectedLake(lakeId)
        setSelectedZone(null)
        setAssets([])
        const data = await apiService.getZones(lakeId)
        setZones(data)
    }

    const handleZoneClick = async (zoneId: string) => {
        setSelectedZone(zoneId)
        const data = await apiService.getAssets(zoneId)
        setAssets(data)
    }

    return (
        <div className="explorer-container">
            <div className="explorer-header flex justify-between items-center">
                <div className="breadcrumb">
                    <span className="breadcrumb-item" onClick={() => { setSelectedLake(null); setSelectedZone(null); }}>Inventory</span>
                    {selectedLake && (
                        <>
                            <ChevronRight size={16} />
                            <span className="breadcrumb-item">{selectedLake}</span>
                        </>
                    )}
                    {selectedZone && (
                        <>
                            <ChevronRight size={16} />
                            <span className="breadcrumb-item">{selectedZone}</span>
                        </>
                    )}
                </div>

                <button className="btn btn-primary btn-sm">
                    <Plus size={16} />
                    <span>New Lake</span>
                </button>
            </div>

            <div className="explorer-grid">
                {/* Lakes Column */}
                <div className="explorer-col">
                    <div className="col-header flex items-center justify-between">
                        <span className="text-muted font-bold">LAKES</span>
                        <Search size={14} className="text-muted" />
                    </div>
                    <div className="col-content">
                        {lakes.map(lake => (
                            <div
                                key={lake.ui_id}
                                className={`resource-item ${selectedLake === lake.ui_id ? 'selected' : ''}`}
                                onClick={() => handleLakeClick(lake.ui_id)}
                            >
                                <Database size={16} className="item-icon lake-icon" />
                                <div className="item-info">
                                    <span className="item-name">{lake.display_name}</span>
                                    <span className="item-meta">{lake.ui_id}</span>
                                </div>
                                <ChevronRight size={14} className="chevron" />
                            </div>
                        ))}
                    </div>
                </div>

                {/* Zones Column */}
                <div className="explorer-col">
                    <div className="col-header flex items-center justify-between">
                        <span className="text-muted font-bold">ZONES</span>
                        <Filter size={14} className="text-muted" />
                    </div>
                    <div className="col-content">
                        {selectedLake ? (
                            zones.length > 0 ? (
                                zones.map(zone => (
                                    <div
                                        key={zone.ui_id}
                                        className={`resource-item ${selectedZone === zone.ui_id ? 'selected' : ''}`}
                                        onClick={() => handleZoneClick(zone.ui_id)}
                                    >
                                        <Folder size={16} className="item-icon zone-icon" />
                                        <div className="item-info">
                                            <span className="item-name">{zone.ui_id.toUpperCase()}</span>
                                            <span className="item-meta">{zone.type}</span>
                                        </div>
                                        <ChevronRight size={14} className="chevron" />
                                    </div>
                                ))
                            ) : (
                                <div className="empty-state">No zones found</div>
                            )
                        ) : (
                            <div className="empty-state">Select a lake</div>
                        )}
                    </div>
                </div>

                {/* Assets Column */}
                <div className="explorer-col">
                    <div className="col-header flex items-center justify-between">
                        <span className="text-muted font-bold">ASSETS</span>
                    </div>
                    <div className="col-content">
                        {selectedZone ? (
                            assets.length > 0 ? (
                                assets.map(asset => (
                                    <div key={asset.ui_id} className="resource-item asset-item">
                                        <FileText size={16} className="item-icon asset-icon" />
                                        <div className="item-info">
                                            <span className="item-name">{asset.ui_id}</span>
                                            <span className="item-meta">{asset.schema}</span>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="empty-state">No assets found</div>
                            )
                        ) : (
                            <div className="empty-state">Select a zone</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Explorer
