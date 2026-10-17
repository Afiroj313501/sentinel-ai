interface FilterChipProps {
  label: string;
  active: boolean;
  onToggle: () => void;
}

export default function FilterChip({ label, active, onToggle }: FilterChipProps) {
  const style = active
    ? "border-indigo-600 bg-indigo-600 text-white"
    : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50";
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onToggle}
      className={`rounded-full border px-3 py-1 text-xs font-medium ${style}`}
    >
      {label}
    </button>
  );
}
