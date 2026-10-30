interface Props {
  label: string;
  value: string;
  hint?: string;
}

export default function KpiCard({ label, value, hint }: Props) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className="card-value">{value}</div>
      {hint && <div className="card-hint">{hint}</div>}
    </div>
  );
}   