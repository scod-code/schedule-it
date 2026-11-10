export default function QualityBadge({ metrics }) {
  if (!metrics) return null
  const { violations, home_away_breaks, balance_score, solve_time_ms } = metrics
  return (
    <div className="flex flex-wrap gap-3 items-center my-4">
      <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold ${
        violations === 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}>
        {violations === 0 ? '✓ No clashes' : `✗ ${violations} clash${violations !== 1 ? 'es' : ''}`}
      </span>
      <span className="text-sm text-gray-600">Home/away breaks: <strong>{home_away_breaks}</strong></span>
      <span className="text-sm text-gray-600">Balance score: <strong>{typeof balance_score === 'number' ? balance_score.toFixed(2) : balance_score}</strong></span>
      <span className="text-xs text-gray-400">Solved in {solve_time_ms}ms</span>
    </div>
  )
}
