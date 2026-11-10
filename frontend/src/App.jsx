import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import PreviewPage from './pages/PreviewPage'
import SuccessPage from './pages/SuccessPage'
import PrivacyPage from './pages/PrivacyPage'
import TermsPage from './pages/TermsPage'
import RefundPage from './pages/RefundPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/preview/:jobId" element={<PreviewPage />} />
        <Route path="/success" element={<SuccessPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/refund" element={<RefundPage />} />
      </Routes>
    </BrowserRouter>
  )
}
