import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function formatPrice(value) {
  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value) {
  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

export default function PriceChart({ data = [] }) {
  if (!data.length) {
    return (
      <div className="chart-empty-state">
        Grafik oluşması için önce veritabanında fiyat kaydı bulunmalı.
      </div>
    );
  }

  const chartData = data.map((item) => ({
    ...item,
    kisaTarih: formatDate(item.tarih),
  }));

  return (
    <div className="chart-shell">
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="rgba(45, 74, 61, 0.14)" vertical={false} />
          <XAxis dataKey="kisaTarih" minTickGap={28} stroke="#3f5e4e" />
          <YAxis stroke="#3f5e4e" tickFormatter={(value) => `${value} TL`} width={92} />
          <Tooltip
            formatter={(value) => formatPrice(value)}
            labelFormatter={(label) => `Tarih: ${label}`}
            contentStyle={{
              backgroundColor: '#f7f1e8',
              border: '1px solid rgba(63, 94, 78, 0.2)',
              borderRadius: '16px',
            }}
          />
          <Line
            type="monotone"
            dataKey="fiyat"
            stroke="#d97841"
            strokeWidth={3}
            dot={{ fill: '#19332a', r: 4 }}
            activeDot={{ r: 7, stroke: '#d97841', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
