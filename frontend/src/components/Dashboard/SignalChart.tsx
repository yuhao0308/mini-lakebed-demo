import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import './SignalChart.css'

interface SignalChartProps {
    title: string
    data: any[]
    color: string
    unit?: string
    type?: 'line' | 'area'
}

const SignalChart: React.FC<SignalChartProps> = ({ title, data, color, unit, type = 'area' }) => {
    return (
        <div className="signal-chart-container glass-panel p-4 rounded border">
            <div className="chart-header">
                <h4 className="chart-title">{title}</h4>
                <div className="chart-current">
                    {data[data.length - 1].value}{unit}
                </div>
            </div>

            <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={150}>
                    {type === 'area' ? (
                        <AreaChart data={data}>
                            <defs>
                                <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" opacity={0.5} />
                            <XAxis dataKey="name" hide />
                            <YAxis hide domain={['auto', 'auto']} />
                            <Tooltip
                                contentStyle={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}
                                itemStyle={{ color: color }}
                            />
                            <Area type="monotone" dataKey="value" stroke={color} fillOpacity={1} fill={`url(#gradient-${title})`} strokeWidth={2} />
                        </AreaChart>
                    ) : (
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" opacity={0.5} />
                            <XAxis dataKey="name" hide />
                            <YAxis hide domain={['auto', 'auto']} />
                            <Tooltip
                                contentStyle={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}
                                itemStyle={{ color: color }}
                            />
                            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
                        </LineChart>
                    )}
                </ResponsiveContainer>
            </div>
        </div>
    )
}

export default SignalChart
