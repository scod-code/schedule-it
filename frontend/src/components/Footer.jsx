import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="border-t border-gray-200 mt-16 py-8 text-center text-sm text-gray-500">
      <p>
        &copy; 2026 Schedule-it &middot;{' '}
        <Link to="/privacy" className="hover:text-indigo-600">Privacy</Link>
        {' '}&middot;{' '}
        <Link to="/terms" className="hover:text-indigo-600">Terms</Link>
        {' '}&middot;{' '}
        <Link to="/refund" className="hover:text-indigo-600">Refund Policy</Link>
      </p>
    </footer>
  )
}
