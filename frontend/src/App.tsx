import { Suspense, lazy, useState } from 'react'
import Layout from './components/Layout/Layout'
import { LanguageProvider } from './hooks/useLanguage'

const Explorer = lazy(() => import('./components/Explorer/Explorer'))
const ChatPane = lazy(() => import('./components/Chat/ChatPane'))
const Dashboard = lazy(() => import('./components/Dashboard/Dashboard'))
const AuditLogs = lazy(() => import('./components/Dashboard/AuditLogs'))

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
    <LanguageProvider>
      <Layout activeView={activeView} onViewChange={setActiveView}>
        <Suspense fallback={<div>Loading view...</div>}>
          {renderView()}
        </Suspense>
      </Layout>
    </LanguageProvider>
  )
}

export default App
