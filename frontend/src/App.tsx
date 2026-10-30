import { createBrowserRouter, RouterProvider } from 'react-router'
import { Layout } from './components/Layout'
import { AdminPage } from './pages/AdminPage'
import { AnalyzingPage } from './pages/AnalyzingPage'
import { InstallPage } from './pages/InstallPage'
import { IntentPage } from './pages/IntentPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ResultPage } from './pages/ResultPage'
import { ScanPage } from './pages/ScanPage'
import { SuggestionsPage } from './pages/SuggestionsPage'
import { ScanFlowProvider } from './state/scanFlow'

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <ScanPage /> },
      { path: '/analyzing', element: <AnalyzingPage /> },
      { path: '/result', element: <ResultPage /> },
      { path: '/intent', element: <IntentPage /> },
      { path: '/suggestions', element: <SuggestionsPage /> },
      { path: '/install', element: <InstallPage /> },
      { path: '/admin', element: <AdminPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default function App() {
  return (
    <ScanFlowProvider>
      <RouterProvider router={router} />
    </ScanFlowProvider>
  )
}
