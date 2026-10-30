import { createBrowserRouter, RouterProvider } from 'react-router'
import { Layout } from './components/Layout'
import { AnalyzingPage } from './pages/AnalyzingPage'
import { InstallPage } from './pages/InstallPage'
import { IntentPage } from './pages/IntentPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { ResultPage } from './pages/ResultPage'
import { ScanPage } from './pages/ScanPage'
import { ScanFlowProvider } from './state/scanFlow'

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <ScanPage /> },
      { path: '/analyzing', element: <AnalyzingPage /> },
      { path: '/result/:analysisId', element: <ResultPage /> },
      { path: '/intent/:analysisId', element: <IntentPage /> },
      { path: '/install', element: <InstallPage /> },
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
