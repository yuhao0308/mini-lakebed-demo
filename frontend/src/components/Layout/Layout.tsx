import React from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import './Layout.css'

interface LayoutProps {
    children: React.ReactNode
    activeView: string
    onViewChange: (view: string) => void
}

const Layout: React.FC<LayoutProps> = ({ children, activeView, onViewChange }) => {
    return (
        <div className="app-layout">
            <Sidebar activeView={activeView} onViewChange={onViewChange} />

            <div className="main-container">
                <Header title={activeView.replace('_', ' ')} />
                <main className="content-area">
                    {children}
                </main>
            </div>
        </div>
    )
}

export default Layout
