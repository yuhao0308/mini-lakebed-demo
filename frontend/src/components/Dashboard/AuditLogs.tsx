import React from 'react'
import { Shield, ExternalLink, Search } from 'lucide-react'
import './AuditLogs.css'

const MOCK_LOGS = [
    { id: 'log_01', timestamp: '2025-12-22 13:30:15', action: 'ESTIMATE_PAYMENT', user: 'agent_user_01', details: 'Rule: LENDER_A_700_PLUS', result: 'Success ($452.12)' },
    { id: 'log_02', timestamp: '2025-12-22 13:28:42', action: 'SEARCH_INVENTORY', user: 'agent_user_01', details: 'Filters: make=Toyota, year>2020', result: '12 items found' },
    { id: 'log_03', timestamp: '2025-12-22 13:25:10', action: 'LIST_ASSETS', user: 'demo_user', details: 'Path: .../zones/curated/assets', result: 'Access Granted' },
    { id: 'log_04', timestamp: '2025-12-22 13:20:05', action: 'CREATE_LAKE', user: 'admin', details: 'ID: finance-lake', result: 'Resource Created' },
    { id: 'log_05', timestamp: '2025-12-22 13:15:33', action: 'ESTIMATE_PAYMENT', user: 'agent_user_01', details: 'Rule: LENDER_B_600_650', result: 'Success ($582.00)' },
]

const AuditLogs: React.FC = () => {
    return (
        <div className="audit-logs-container">
            <div className="audit-header flex justify-between items-center">
                <div>
                    <h1 className="audit-title">Audit Logs</h1>
                    <p className="text-muted">Traceability and governance records for all platform operations.</p>
                </div>
                <div className="flex gap-2">
                    <button className="btn btn-secondary flex items-center gap-2">
                        <Search size={16} />
                        Filter Logs
                    </button>
                </div>
            </div>

            <div className="glass-panel rounded border overflow-hidden">
                <table className="audit-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Action</th>
                            <th>Principal</th>
                            <th>Details</th>
                            <th>Result</th>
                            <th>Trace</th>
                        </tr>
                    </thead>
                    <tbody>
                        {MOCK_LOGS.map(log => (
                            <tr key={log.id}>
                                <td className="font-mono text-xs">{log.timestamp}</td>
                                <td>
                                    <span className={`action-badge ${log.action}`}>
                                        {log.action}
                                    </span>
                                </td>
                                <td className="text-sm font-medium">{log.user}</td>
                                <td className="text-sm italic text-muted max-w-[300px] truncate" title={log.details}>
                                    {log.details}
                                </td>
                                <td className="text-sm">{log.result}</td>
                                <td>
                                    <button className="icon-btn" title="View Trace Object">
                                        <ExternalLink size={14} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="mt-6 flex items-center justify-between text-xs text-muted">
                <div className="flex items-center gap-2">
                    <Shield size={14} className="text-success" />
                    <span>All logs are immutable and stored in a governed lake zone.</span>
                </div>
                <span>Showing 5 of 1,242 records</span>
            </div>
        </div>
    )
}

export default AuditLogs
