import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-12">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 prose prose-sm max-w-none">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">Privacy Policy</h1>
          <p className="text-gray-500 text-sm mb-6">Last updated: January 2026</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">What data we collect</h2>
          <p className="text-gray-600 text-sm">When you use Schedule-it, we store the schedule data you enter (teams, venues, time slots) and the generated schedule output. We do not collect any personal information or require you to create an account.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">How long we keep it</h2>
          <p className="text-gray-600 text-sm">All schedule data is automatically deleted after 30 days. We do not retain payment information — this is handled entirely by Stripe.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Payments</h2>
          <p className="text-gray-600 text-sm">Payment processing is handled by Stripe. We never see or store your card details. Please refer to <a href="https://stripe.com/privacy" className="text-indigo-600 hover:underline" target="_blank" rel="noreferrer">Stripe&apos;s privacy policy</a> for details on how payment data is handled.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Third parties</h2>
          <p className="text-gray-600 text-sm">We do not sell, share, or transfer your data to any third parties. We use no analytics or advertising trackers.</p>

          <h2 className="font-semibold text-gray-800 mt-6 mb-2">Your rights</h2>
          <p className="text-gray-600 text-sm">As your data is anonymous and automatically deleted after 30 days, there is no personal data to request or delete. If you have any questions, please contact us.</p>
        </div>
      </main>
      <Footer />
    </div>
  )
}
