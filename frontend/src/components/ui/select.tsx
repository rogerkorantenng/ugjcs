import { type SelectHTMLAttributes, forwardRef } from "react";

interface FieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
}

export const Select = forwardRef<HTMLSelectElement, FieldProps>(function Select(
  { label, id, name, children, className = "", ...props },
  ref,
) {
  const fieldId = id ?? name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink">{label}</label>
      <select
        ref={ref}
        id={fieldId}
        name={name}
        className={`w-full rounded-[3px] border border-rule bg-white px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(18,32,58,0.04)]
          transition-colors duration-150 hover:border-stamp/40
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp focus-visible:border-stamp/60 ${className}`}
        {...props}
      >
        {children}
      </select>
    </div>
  );
});
