interface FilterChipProps {
  label: string;
  active: boolean;
  onToggle: () => void;
}

export default function FilterChip({ label, active, onToggle }: FilterChipProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onToggle}
      className={`chip${active ? " active" : ""}`}
    >
      {label}
    </button>
  );
}
