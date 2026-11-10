import { useForm, useFieldArray } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { generateSchedule } from '../api/scheduleApi'
import VenueFields from './VenueFields'
import SlotFields from './SlotFields'

export default function ScheduleForm() {
  const navigate = useNavigate()
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm({
    defaultValues: {
      league_name: '',
      teams_text: '',
      venues: [{ name: '', capacity: '' }, { name: '', capacity: '' }],
      slots: [
        { date: '', time: '', venue_name: '' },
        { date: '', time: '', venue_name: '' },
        { date: '', time: '', venue_name: '' },
      ],
      blackout_dates_text: '',
      round_robin: 'single',
      derby_pairs_text: '',
      max_consecutive_home: 3,
      max_consecutive_away: 3,
    },
  })

  const { fields: venueFields, append: appendVenue, remove: removeVenue } = useFieldArray({ control, name: 'venues' })
  const { fields: slotFields, append: appendSlot, remove: removeSlot } = useFieldArray({ control, name: 'slots' })

  const onSubmit = async (data) => {
    const teams = data.teams_text.split('\n').map(t => t.trim()).filter(Boolean)
    if (teams.length < 4) {
      setError('teams_text', { message: 'Please enter at least 4 teams.' })
      return
    }

    const venues = data.venues.map(v => ({ name: v.name.trim(), capacity: Number(v.capacity) }))
    const slots = data.slots.map(s => ({ date: s.date, time: s.time, venue_name: s.venue_name.trim() }))

    const blackout_dates = data.blackout_dates_text
      ? data.blackout_dates_text.split('\n').map(d => d.trim()).filter(Boolean)
      : []

    const derby_pairs = data.derby_pairs_text
      ? data.derby_pairs_text.split('\n').map(line => line.split(' vs ').map(t => t.trim())).filter(pair => pair.length === 2 && pair[0] && pair[1])
      : []

    const payload = {
      teams,
      venues,
      slots,
      round_robin: data.round_robin,
      blackout_dates,
      derby_pairs,
      max_consecutive_home: Number(data.max_consecutive_home),
      max_consecutive_away: Number(data.max_consecutive_away),
    }

    try {
      const res = await generateSchedule(payload)
      const { job_id, preview, teams: teamsList } = res.data
      localStorage.setItem('schedule_it_job_id', job_id)
      navigate(`/preview/${job_id}`, {
        state: {
          preview,
          teams: teamsList,
          leagueName: data.league_name,
        },
      })
    } catch (err) {
      const detail = err?.response?.data?.detail
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map(d => d.msg || JSON.stringify(d)).join(', ')
          : 'Failed to generate schedule. Please check your inputs and try again.'
      setError('root', { message })
    }
  }

  const inputClass = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'
  const labelClass = 'block text-sm font-semibold text-gray-700 mb-1'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8" id="schedule-form">
      {/* League Name */}
      <div>
        <label className={labelClass}>League name <span className="font-normal text-gray-400">(optional)</span></label>
        <input type="text" placeholder="e.g. Sunday 5-a-side 2026" {...register('league_name')} className={inputClass} />
      </div>

      {/* Teams */}
      <div>
        <label className={labelClass}>Teams <span className="text-red-500">*</span></label>
        <textarea
          rows={6}
          placeholder={`Arsenal\nChelsea\nLiverpool\nManchester City\nTottenham`}
          {...register('teams_text', { required: 'Please enter at least 4 teams.' })}
          className={inputClass + ' resize-y'}
        />
        <p className="text-xs text-gray-500 mt-1">One team per line. Min 4 teams.</p>
        {errors.teams_text && <p className="text-red-500 text-sm mt-1">{errors.teams_text.message}</p>}
      </div>

      {/* Venues */}
      <div>
        <label className={labelClass}>Venues <span className="text-red-500">*</span></label>
        <div className="space-y-3">
          {venueFields.map((field, index) => (
            <VenueFields key={field.id} register={register} index={index} remove={removeVenue} errors={errors} />
          ))}
        </div>
        <button
          type="button"
          onClick={() => appendVenue({ name: '', capacity: '' })}
          className="mt-3 text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add venue
        </button>
      </div>

      {/* Time Slots */}
      <div>
        <label className={labelClass}>Time slots <span className="text-red-500">*</span></label>
        <div className="hidden md:flex gap-3 text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
          <span className="flex-1">Date</span>
          <span className="w-28">Time</span>
          <span className="flex-1">Venue name</span>
          <span className="w-5" />
        </div>
        <div className="space-y-3">
          {slotFields.map((field, index) => (
            <SlotFields key={field.id} register={register} index={index} remove={removeSlot} errors={errors} />
          ))}
        </div>
        <button
          type="button"
          onClick={() => appendSlot({ date: '', time: '', venue_name: '' })}
          className="mt-3 text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add slot
        </button>
      </div>

      {/* Blackout Dates */}
      <div>
        <label className={labelClass}>Blackout dates <span className="font-normal text-gray-400">(optional)</span></label>
        <textarea
          rows={3}
          placeholder={`2026-12-25\n2026-01-01`}
          {...register('blackout_dates_text')}
          className={inputClass + ' resize-y'}
        />
        <p className="text-xs text-gray-500 mt-1">One date per line in YYYY-MM-DD format. No matches will be scheduled on these dates.</p>
      </div>

      {/* Round Robin */}
      <div>
        <label className={labelClass}>Format <span className="text-red-500">*</span></label>
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" value="single" {...register('round_robin')} className="text-indigo-600" />
            <span className="text-sm text-gray-700">Single round robin <span className="text-gray-400">(each pair plays once)</span></span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" value="double" {...register('round_robin')} className="text-indigo-600" />
            <span className="text-sm text-gray-700">Double round robin <span className="text-gray-400">(each pair plays twice, home and away)</span></span>
          </label>
        </div>
      </div>

      {/* Derby Pairs */}
      <div>
        <label className={labelClass}>Derby pairs <span className="font-normal text-gray-400">(optional)</span></label>
        <textarea
          rows={3}
          placeholder={`Arsenal vs Chelsea\nLiverpool vs Manchester City`}
          {...register('derby_pairs_text')}
          className={inputClass + ' resize-y'}
        />
        <p className="text-xs text-gray-500 mt-1">One pair per line using &quot;Team A vs Team B&quot; format. Derby matches won&apos;t be scheduled in the first few rounds.</p>
      </div>

      {/* Max Consecutive */}
      <div>
        <label className={labelClass}>Consecutive match limits</label>
        <div className="flex gap-6">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Max consecutive home</label>
            <input
              type="number"
              min={1}
              max={10}
              {...register('max_consecutive_home', { valueAsNumber: true, min: 1, max: 10 })}
              className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Max consecutive away</label>
            <input
              type="number"
              min={1}
              max={10}
              {...register('max_consecutive_away', { valueAsNumber: true, min: 1, max: 10 })}
              className="w-24 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      </div>

      {errors.root && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-red-700 text-sm">
          {errors.root.message}
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-3 px-6 bg-indigo-600 text-white rounded-xl font-semibold text-base hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Generating...
          </>
        ) : 'Generate Schedule →'}
      </button>
    </form>
  )
}
