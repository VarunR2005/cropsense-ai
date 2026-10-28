export const num = (v, d = 2) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "-"
    : Number(v).toLocaleString(undefined, { maximumFractionDigits: d });

export const pct = (v) => (v === null || v === undefined ? "-" : `${v > 0 ? "+" : ""}${v}%`);

// "" -> undefined so empty optional inputs are not sent to the API
export const toNum = (v) => (v === "" || v === null || v === undefined ? undefined : Number(v));

export const dateOnly = (iso) => (iso ? String(iso).slice(0, 10) : "-");
