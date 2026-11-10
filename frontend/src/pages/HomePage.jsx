import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import ScheduleForm from '../components/ScheduleForm'

const features = [
  { icon: '⚡', title: 'No clashes guaranteed', desc: 'Our constraint solver ensures no team plays twice in the same slot and venues are never double-booked.' },
  { icon: '⚖️', title: 'Fair home/away balance', desc: 'Every team gets a fair split of home and away matches, minimising consecutive runs.' },
  { icon: '📄', title: 'Export to PDF, CSV, Calendar', desc: 'Download a formatted PDF, a spreadsheet, and individual .ics calendar files for every team.' },
]

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1">
        {/* Hero */}
        <section className="bg-white py-20 px-4 text-center border-b border-gray-100">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 leading-tight">
              Generate clash-free fixtures<br className="hidden md:block" /> in seconds
            </h1>
            <p className="mt-5 text-lg text-gray-500 max-w-xl mx-auto">
              Enter your teams, venues, and time slots. Get a complete season schedule as PDF, CSV, and calendar files. Pay once — no account needed.
            </p>
            <a
              href="#schedule-form"
              className="mt-8 inline-block px-8 py-3 bg-indigo-600 text-white rounded-xl font-semibold text-lg hover:bg-indigo-700 transition-colors"
            >
              Get started — it&apos;s free to preview
            </a>
          </div>
        </section>

        {/* Features */}
        <section className="py-14 px-4 max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {features.map(f => (
              <div key={f.title} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-gray-900 mb-1">{f.title}</h3>
                <p className="text-sm text-gray-500">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Form */}
        <section className="py-10 px-4 max-w-2xl mx-auto">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Build your schedule</h2>
            <ScheduleForm />
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
