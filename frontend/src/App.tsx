import { useState } from 'react'
import Layout from './components/Layout/Layout'
import Explorer from './components/Explorer/Explorer'
import ChatPane from './components/Chat/ChatPane'
import Dashboard from './components/Dashboard/Dashboard'
import AuditLogs from './components/Dashboard/AuditLogs'

function App() {
  const [activeView, setActiveView] = useState('explorer')

  const renderView = () => {
    switch (activeView) {
      case 'explorer':
        return <Explorer />
      case 'chat':
        return <ChatPane />
      case 'dashboard':
        return <Dashboard />
      case 'audit':
        return <AuditLogs />
      default:
        return <div>Select a view from the sidebar.</div>
    }
  }

  return (
    <Layout activeView={activeView} onViewChange={setActiveView}>
      {renderView()}
    </Layout>
  )
}

export default App
