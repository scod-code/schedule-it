import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function TermsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-12">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">Terms of Service</h1>
          <p className="text-gray-500 text-sm mb-6">Last updated: January 2026</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Service</h2>
          <p className="text-gray-600 text-sm">Schedule-it is a one-off scheduling tool. You pay once per schedule and receive access to download files. There is no subscription, no account, and no recurring charge.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Payment</h2>
          <p className="text-gray-600 text-sm">The fee of £9 is a one-off payment for a single generated schedule. Payment is processed securely by Stripe. Once payment is confirmed, your download links are made available immediately.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Licence</h2>
          <p className="text-gray-600 text-sm">The generated schedule is provided for your personal or organisational use. You may distribute it freely within your league or organisation. You may not resell the generated output.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Availability</h2>
          <p className="text-gray-600 text-sm">Download links remain active for 30 days after payment. We recommend downloading all files promptly after purchase. We are not responsible for files that have expired.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Limitation of liability</h2>
          <p className="text-gray-600 text-sm">Schedule-it is provided as-is. We make no guarantees about uptime or suitability for any particular purpose. Our maximum liability is limited to the amount you paid.</p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
