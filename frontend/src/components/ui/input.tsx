import { type InputHTMLAttributes, forwardRef } from "react";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  /** Stated before submission, not just after rejection — the requirement a validation
   * error would otherwise be the reader's first notice of. */
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, FieldProps>(function Input(
  { label, error, hint, id, className = "", ...props },
  ref,
) {
  const inputId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  return (
    <div>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="mb-1.5 text-xs text-ink/55">
          {hint}
        </p>
      )}
      <input
        ref={ref}
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
        className={`w-full rounded-[3px] border bg-white px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(18,32,58,0.04)]
          transition-colors duration-150 placeholder:text-ink/35
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp focus-visible:border-stamp/60
          ${error ? "border-seal" : "border-rule hover:border-stamp/40"} ${className}`}
        {...props}
      />
      {error && (
        <p id={errorId} className="mt-1 text-sm text-seal">
          {error}
        </p>
      )}
    </div>
  );
});
