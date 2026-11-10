import { useEffect, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import DownloadLinks from '../components/DownloadLinks'
import { getJob } from '../api/scheduleApi'

export default function SuccessPage() {
  const { state } = useLocation()
  const [searchParams] = useSearchParams()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const jobId = state?.jobId || localStorage.getItem('schedule_it_job_id')
    if (!jobId) {
      setError('Could not find your job. Please check your email or contact support.')
      setLoading(false)
      return
    }
    getJob(jobId)
      .then(r => setJob(r.data))
      .catch(() => setError('Failed to load your schedule. Please contact support.'))
      .finally(() => setLoading(false))
  }, [])

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
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-16">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          {error ? (
            <div className="text-red-700 text-center">{error}</div>
          ) : (
            <>
              <div className="text-center mb-8">
                <div className="text-5xl mb-4">✓</div>
                <h1 className="text-2xl font-bold text-gray-900">Payment successful!</h1>
                <p className="text-gray-500 mt-2">Your schedule is ready to download.</p>
              </div>
              {job && <DownloadLinks jobId={job.job_id} teams={job.teams} />}
              <p className="text-xs text-gray-400 text-center mt-8">
                Files available for 30 days. Made with schedule-it.com
              </p>
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}
