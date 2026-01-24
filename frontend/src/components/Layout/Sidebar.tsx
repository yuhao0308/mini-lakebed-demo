import React from 'react'
import { MessageSquare, Database, Activity, History, Settings, ChevronRight } from 'lucide-react'
import './Sidebar.css'

interface SidebarProps {
    activeView: string
    onViewChange: (view: string) => void
}

const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange }) => {
    const menuItems = [
        { id: 'explorer', label: 'Asset Explorer', icon: Database },
        { id: 'chat', label: 'AI Assistant', icon: MessageSquare },
        { id: 'dashboard', label: 'Golden Signals', icon: Activity },
        { id: 'audit', label: 'Audit Logs', icon: History },
    ]

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="logo-container">
                    <div className="logo-icon">ML</div>
                    <span className="logo-text">Mini-Lakebed</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        className={`nav-item ${activeView === item.id ? 'active' : ''}`}
                        onClick={() => onViewChange(item.id)}
                    >
                        <item.icon size={20} />
                        <span>{item.label}</span>
                        {activeView === item.id && <ChevronRight size={16} className="active-indicator" />}
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <button className="nav-item">
                    <Settings size={20} />
                    <span>Settings</span>
                </button>
                <div className="demo-badge">DEMO MODE</div>
            </div>
        </aside>
    )
}

export default Sidebar
