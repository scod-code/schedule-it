import { downloadUrl } from '../api/scheduleApi'

export default function DownloadLinks({ jobId, teams }) {
  const btn = 'inline-block px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors'
  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-semibold text-gray-800 mb-2">Full Schedule PDF</h3>
        <a href={downloadUrl(jobId, 'pdf')} target="_blank" rel="noreferrer" className={btn}>
          Download PDF
        </a>
      </div>
      <div>
        <h3 className="font-semibold text-gray-800 mb-2">Spreadsheet (CSV)</h3>
        <a href={downloadUrl(jobId, 'csv')} target="_blank" rel="noreferrer" className={btn}>
          Download CSV
        </a>
      </div>
      <div>
        <h3 className="font-semibold text-gray-800 mb-2">Calendar Files (.ics)</h3>
        <div className="flex flex-wrap gap-2">
          {(teams || []).map(team => (
            <a key={team} href={downloadUrl(jobId, 'ics', team)} target="_blank" rel="noreferrer" className={btn}>
              {team}
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
