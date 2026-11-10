export default function SlotFields({ register, index, remove, errors }) {
  return (
    <div className="flex gap-3 items-start flex-wrap md:flex-nowrap">
      <div className="w-full md:w-auto md:flex-1">
        <input
          type="date"
          {...register(`slots.${index}.date`, { required: 'Date required' })}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors?.slots?.[index]?.date && (
          <p className="text-red-500 text-xs mt-1">{errors.slots[index].date.message}</p>
        )}
      </div>
      <div className="w-full md:w-28">
        <input
          type="time"
          {...register(`slots.${index}.time`, { required: 'Time required' })}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors?.slots?.[index]?.time && (
          <p className="text-red-500 text-xs mt-1">{errors.slots[index].time.message}</p>
        )}
      </div>
      <div className="w-full md:flex-1">
        <input
          type="text"
          placeholder="Venue name"
          {...register(`slots.${index}.venue_name`, { required: 'Venue required' })}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors?.slots?.[index]?.venue_name && (
          <p className="text-red-500 text-xs mt-1">{errors.slots[index].venue_name.message}</p>
        )}
      </div>
      <button type="button" onClick={() => remove(index)} className="mt-1 text-gray-400 hover:text-red-500 transition-colors" aria-label="Remove slot">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}
