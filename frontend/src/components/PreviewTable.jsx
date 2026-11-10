export default function PreviewTable({ matches, remainingCount }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {['Round', 'Date', 'Time', 'Home Team', 'Away Team', 'Venue'].map(h => (
              <th key={h} className="px-4 py-3 text-left font-semibold text-gray-600 uppercase tracking-wide text-xs">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {matches.map((m, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-700">{m.round_num}</td>
              <td className="px-4 py-3 text-gray-700">{m.date}</td>
              <td className="px-4 py-3 text-gray-700">{m.time}</td>
              <td className="px-4 py-3 font-medium text-gray-900">{m.home_team}</td>
              <td className="px-4 py-3 text-gray-700">{m.away_team}</td>
              <td className="px-4 py-3 text-gray-500">{m.venue}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {remainingCount > 0 && (
        <div className="relative mt-2">
          <div className="blur-sm opacity-50 pointer-events-none">
            <table className="min-w-full text-sm">
              <tbody className="divide-y divide-gray-100">
                {Array.from({ length: Math.min(remainingCount, 3) }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-20" /></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-white rounded-xl shadow-lg px-6 py-4 text-center border border-indigo-100">
              <span className="text-2xl">🔒</span>
              <p className="mt-1 font-semibold text-gray-800">{remainingCount} more match{remainingCount !== 1 ? 'es' : ''} locked</p>
              <p className="text-sm text-gray-500">Unlock to see the full schedule</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
