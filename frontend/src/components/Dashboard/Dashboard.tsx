import React from 'react'
import SignalChart from './SignalChart'
import './Dashboard.css'

const generateMockData = (base: number, volatility: number, count: number = 20) => {
    return Array.from({ length: count }).map((_, i) => ({
        name: i.toString(),
        value: Math.floor(base + Math.random() * volatility)
    }))
}

const Dashboard: React.FC = () => {
    const signalData = {
        latency: generateMockData(120, 80),
        traffic: generateMockData(450, 150),
        errors: generateMockData(0, 5),
        saturation: generateMockData(20, 60)
    }

    return (
        <div className="dashboard-container">
            <div className="dashboard-header flex justify-between items-center">
                <div>
                    <h1 className="dashboard-title">Observability</h1>
                    <p className="text-muted">Real-time SRE Golden Signals for the Mini-Lakebed Portal.</p>
                </div>
                <div className="flex gap-2">
                    <div className="status-indicator active">
                        <span className="dot"></span>
                        SYSTEM HEALTHY
                    </div>
                </div>
            </div>

            <div className="dashboard-grid">
                <SignalChart
                    title="Latency"
                    data={signalData.latency}
                    color="var(--color-primary)"
                    unit="ms"
                />
                <SignalChart
                    title="Traffic"
                    data={signalData.traffic}
                    color="var(--color-info)"
                    unit=" req/s"
                />
                <SignalChart
                    title="Errors"
                    data={signalData.errors}
                    color="var(--color-error)"
                    unit="%"
                    type="line"
                />
                <SignalChart
                    title="Saturation"
                    data={signalData.saturation}
                    color="var(--color-warning)"
                    unit="%"
                />
            </div>

            <div className="glass-panel p-6 rounded border mt-4">
                <h3 className="mb-4">Compute Resources</h3>
                <div className="resource-bars flex flex-col gap-4">
                    <div className="bar-group">
                        <div className="flex justify-between mb-1">
                            <span className="text-sm font-medium">Memory Usage (Mac mini M4)</span>
                            <span className="text-sm">4.2 GB / 16 GB</span>
                        </div>
                        <div className="bar-bg"><div className="bar-fill" style={{ width: '26%', background: 'var(--color-success)' }}></div></div>
                    </div>
                    <div className="bar-group">
                        <div className="flex justify-between mb-1">
                            <span className="text-sm font-medium">Neural Engine Utilization</span>
                            <span className="text-sm">12%</span>
                        </div>
                        <div className="bar-bg"><div className="bar-fill" style={{ width: '12%', background: 'var(--color-primary)' }}></div></div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Dashboard
