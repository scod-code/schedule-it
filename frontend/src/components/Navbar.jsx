import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function Navbar() {
  const [open, setOpen] = useState(false)
  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-indigo-600">Schedule-it</Link>
        <button className="md:hidden p-2" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={open ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} />
          </svg>
        </button>
        <div className={`${open ? 'flex' : 'hidden'} md:flex flex-col md:flex-row absolute md:static top-full left-0 w-full md:w-auto bg-white md:bg-transparent border-b md:border-0 border-gray-200 md:items-center gap-1 md:gap-4 px-4 md:px-0 py-2 md:py-0`}>
          <Link to="/privacy" className="text-sm text-gray-600 hover:text-indigo-600 py-1">Privacy</Link>
          <Link to="/terms" className="text-sm text-gray-600 hover:text-indigo-600 py-1">Terms</Link>
          <Link to="/refund" className="text-sm text-gray-600 hover:text-indigo-600 py-1">Refund Policy</Link>
        </div>
      </div>
    </nav>
  )
}
