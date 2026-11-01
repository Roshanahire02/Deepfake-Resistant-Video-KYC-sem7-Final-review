// Minimal generic table -- columns: [{ key, header, render? }], rows: array of objects.
// Kept intentionally simple (no sorting/pagination) since the case
// lists this backs are small for an academic prototype.
export default function DataTable({ columns, rows, keyField = 'id', onRowClick, emptyMessage = 'No records found.' }) {
  if (!rows || rows.length === 0) {
    return <div className="py-10 text-center text-sm text-text-muted">{emptyMessage}</div>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border-soft text-xs uppercase tracking-wide text-text-faint">
            {columns.map((col) => (
              <th key={col.key} className="px-3 py-2 font-medium">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row[keyField]}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-border-soft/60 last:border-0 ${
                onRowClick ? 'cursor-pointer hover:bg-surface-raised' : ''
              }`}
              tabIndex={onRowClick ? 0 : undefined}
              role={onRowClick ? 'button' : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === 'Enter') onRowClick(row)
                    }
                  : undefined
              }
            >
              {columns.map((col) => (
                <td key={col.key} className="px-3 py-3 text-text">
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
