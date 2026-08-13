import { type SelectHTMLAttributes, forwardRef } from "react";

interface FieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
}

export const Select = forwardRef<HTMLSelectElement, FieldProps>(function Select(
  { label, hint, id, name, children, className = "", ...props },
  ref,
) {
  const fieldId = id ?? name ?? label.toLowerCase().replace(/\s+/g, "-");
  const hintId = hint ? `${fieldId}-hint` : undefined;
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink">{label}</label>
      {hint && <p id={hintId} className="mb-1.5 text-xs text-ink/60">{hint}</p>}
      <select
        ref={ref}
        id={fieldId}
        name={name}
        aria-describedby={hintId}
        className={`w-full rounded-[3px] border border-rule bg-surface px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(18,21,26,0.04)]
          transition-colors duration-150 hover:border-stamp/40
          focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:border-stamp/60 ${className}`}
        {...props}
      >
        {children}
      </select>
    </div>
  );
});
