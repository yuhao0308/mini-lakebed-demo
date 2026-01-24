import React from 'react'
import { Bell, Search, User } from 'lucide-react'
import './Header.css'

interface HeaderProps {
    title: string
}

const Header: React.FC<HeaderProps> = ({ title }) => {
    return (
        <header className="main-header glass-panel">
            <div className="header-left">
                <h2 className="header-title">{title}</h2>
            </div>

            <div className="header-right">
                <div className="search-bar">
                    <Search size={18} className="search-icon" />
                    <input type="text" placeholder="Search resources..." className="search-input" />
                </div>

                <div className="header-actions">
                    <button className="icon-btn">
                        <Bell size={20} />
                        <span className="notification-dot"></span>
                    </button>
                    <div className="user-profile">
                        <div className="avatar">
                            <User size={20} />
                        </div>
                        <span className="username">Demo User</span>
                    </div>
                </div>
            </div>
        </header>
    )
}

export default Header
