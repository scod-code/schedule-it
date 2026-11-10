import { useEffect, useState } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import PreviewTable from '../components/PreviewTable'
import QualityBadge from '../components/QualityBadge'
import { getJob, createCheckout } from '../api/scheduleApi'

export default function PreviewPage() {
  const { jobId } = useParams()
  const { state } = useLocation()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(!state)
  const [paying, setPaying] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!state) {
      getJob(jobId)
        .then(r => setJob(r.data))
        .catch(() => setError('Could not load job. Please try again.'))
        .finally(() => setLoading(false))
    }
  }, [jobId, state])

  const preview = state?.preview
  const teams = state?.teams || job?.teams || []
  const matches = preview?.matches || []
  const remainingCount = preview?.remaining_count ?? 0
  const metrics = preview?.quality_metrics

  const handleUnlock = async () => {
    setPaying(true)
    setError('')
    try {
      const res = await createCheckout(jobId)
      window.location.href = res.data.checkout_url
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to start checkout. Please try again.')
      setPaying(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-10">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Your Fixture Schedule Preview</h1>
        <p className="text-gray-500 text-sm mb-6">Showing the first rounds. Unlock to access the full schedule.</p>

        {metrics && <QualityBadge metrics={metrics} />}

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden mb-8">
          <PreviewTable matches={matches} remainingCount={remainingCount} />
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-red-700 text-sm mb-4">
            {error}
          </div>
        )}

        <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-8 text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Unlock the full schedule for £9</h2>
          <ul className="text-sm text-gray-600 space-y-1 mb-6 inline-block text-left">
            <li>✅ Every round — all matches for the full season</li>
            <li>✅ Formatted PDF ready to print or share</li>
            <li>✅ CSV spreadsheet for further editing</li>
            <li>✅ Individual .ics calendar file for each team</li>
          </ul>
          <div>
            <button
              onClick={handleUnlock}
              disabled={paying}
              className="px-10 py-3 bg-indigo-600 text-white rounded-xl font-semibold text-lg hover:bg-indigo-700 disabled:opacity-60 transition-colors inline-flex items-center gap-2"
            >
              {paying ? (
                <>
                  <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Redirecting...
                </>
              ) : 'Unlock Now — £9'}
            </button>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
