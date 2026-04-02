export default function LineItemEditor({ items, onChange }) {
  const add = () =>
    onChange([...items, { description: '', quantity: 1, unit_price: 0 }])

  const remove = (i) => onChange(items.filter((_, idx) => idx !== i))

  const update = (i, field, value) => {
    const next = [...items]
    next[i] = { ...next[i], [field]: value }
    onChange(next)
  }

  const total = items.reduce(
    (sum, item) => sum + Number(item.quantity) * Number(item.unit_price),
    0
  )

  return (
    <div>
      <div className="border border-gray-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr className="text-left text-gray-500 border-b border-gray-200">
              <th className="px-3 py-2 font-medium">Description</th>
              <th className="px-3 py-2 font-medium w-20">Qty</th>
              <th className="px-3 py-2 font-medium w-28">Unit Price</th>
              <th className="px-3 py-2 font-medium w-24 text-right">Subtotal</th>
              <th className="px-3 py-2 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((item, i) => (
              <tr key={i}>
                <td className="px-3 py-2">
                  <input
                    type="text"
                    className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    value={item.description}
                    onChange={(e) => update(i, 'description', e.target.value)}
                    placeholder="Description"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    value={item.quantity}
                    onChange={(e) => update(i, 'quantity', e.target.value)}
                  />
                </td>
                <td className="px-3 py-2">
                  <div className="relative">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      className="w-full border border-gray-200 rounded pl-5 pr-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                      value={item.unit_price}
                      onChange={(e) => update(i, 'unit_price', e.target.value)}
                    />
                  </div>
                </td>
                <td className="px-3 py-2 text-right font-medium text-gray-700">
                  ${(Number(item.quantity) * Number(item.unit_price)).toFixed(2)}
                </td>
                <td className="px-3 py-2 text-center">
                  <button
                    type="button"
                    onClick={() => remove(i)}
                    className="text-gray-300 hover:text-red-500 transition-colors text-lg leading-none"
                    aria-label="Remove line item"
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between items-center mt-3">
        <button
          type="button"
          onClick={add}
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          + Add line item
        </button>
        <p className="text-sm font-semibold text-gray-800">
          Total: ${total.toFixed(2)}
        </p>
      </div>
    </div>
  )
}
