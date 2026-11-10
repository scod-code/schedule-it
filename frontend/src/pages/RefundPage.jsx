import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function RefundPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-12">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">Refund Policy</h1>
          <p className="text-gray-500 text-sm mb-6">Last updated: January 2026</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">When we offer refunds</h2>
          <p className="text-gray-600 text-sm">We offer a full refund in the following cases:</p>
          <ul className="list-disc list-inside text-sm text-gray-600 mt-2 space-y-1">
            <li>The schedule generation failed or returned an error.</li>
            <li>The generated schedule is infeasible (no valid fixture set could be found).</li>
            <li>You were charged but did not receive access to your download links.</li>
          </ul>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">How to request a refund</h2>
          <p className="text-gray-600 text-sm">Email us at <a href="mailto:support@schedule-it.com" className="text-indigo-600 hover:underline">support@schedule-it.com</a> with your job ID (shown in the URL after generation). We will process your refund within 5 business days.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Non-refundable cases</h2>
          <p className="text-gray-600 text-sm">We cannot offer refunds if you simply change your mind after a successful schedule has been generated and download links provided, or if the schedule was generated correctly but does not meet requirements you did not specify during generation.</p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
