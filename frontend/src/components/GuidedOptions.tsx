import type { GuidedOption } from '../types';

interface Props {
  options: GuidedOption[];
  onSelect: (option: GuidedOption) => void;
  disabled?: boolean;
}

export function GuidedOptions({ options, onSelect, disabled }: Props) {
  if (!options.length) return null;

  return (
    <div style={styles.container}>
      {options.map((opt, i) => (
        <button
          key={i}
          style={{
            ...styles.btn,
            ...(disabled ? styles.btnDisabled : {}),
          }}
          onClick={() => !disabled && onSelect(opt)}
          disabled={disabled}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    padding: '8px 0',
  },
  btn: {
    padding: '6px 16px',
    borderRadius: 16,
    border: '1px solid #d4c5b9',
    backgroundColor: '#faf6f1',
    color: '#6b5b4f',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all 0.15s',
    whiteSpace: 'nowrap',
  },
  btnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
};
