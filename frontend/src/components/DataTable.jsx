// columns: [{ label, get: (row) => value }]
export default function DataTable({ columns, rows, empty = "No data." }) {
  if (!rows || rows.length === 0) return <p className="text-muted mb-0">{empty}</p>;
  return (
    <div className="table-responsive">
      <table className="table table-sm table-striped align-middle mb-0">
        <thead className="table-success">
          <tr>
            {columns.map((c) => (
              <th key={c.label} scope="col">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.label}>{c.get(r)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
