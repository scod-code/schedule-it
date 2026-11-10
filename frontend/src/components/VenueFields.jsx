export default function VenueFields({ register, index, remove, errors }) {
  return (
    <div className="flex gap-3 items-start">
      <div className="flex-1">
        <input
          type="text"
          placeholder="Venue name"
          {...register(`venues.${index}.name`, { required: 'Venue name required' })}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors?.venues?.[index]?.name && (
          <p className="text-red-500 text-xs mt-1">{errors.venues[index].name.message}</p>
        )}
      </div>
      <div className="w-28">
        <input
          type="number"
          placeholder="Capacity"
          min={1}
          {...register(`venues.${index}.capacity`, { required: 'Required', valueAsNumber: true, min: { value: 1, message: 'Min 1' } })}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors?.venues?.[index]?.capacity && (
          <p className="text-red-500 text-xs mt-1">{errors.venues[index].capacity.message}</p>
        )}
      </div>
      <button type="button" onClick={() => remove(index)} className="mt-1 text-gray-400 hover:text-red-500 transition-colors" aria-label="Remove venue">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}
