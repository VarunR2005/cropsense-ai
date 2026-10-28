import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const COLORS = ["#2e7d32", "#a1887f", "#f9a825"];

// chart: { title, type: "line" | "bar", x: [...], series: [{ name, values: [...] }] }
export default function ReportChart({ chart, height = 260 }) {
  const data = chart.x.map((x, i) => {
    const row = { x };
    chart.series.forEach((s) => {
      row[s.name] = s.values[i];
    });
    return row;
  });
  const Chart = chart.type === "line" ? LineChart : BarChart;
  return (
    <div className="mb-4">
      <h3 className="h6 fw-semibold">{chart.title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <Chart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="x" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          {chart.series.length > 1 && <Legend />}
          {chart.series.map((s, i) =>
            chart.type === "line" ? (
              <Line key={s.name} type="monotone" dataKey={s.name} stroke={COLORS[i % 3]} strokeWidth={2} dot={false} />
            ) : (
              <Bar key={s.name} dataKey={s.name} fill={COLORS[i % 3]} />
            )
          )}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}
