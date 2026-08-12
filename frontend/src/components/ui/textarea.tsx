import { type TextareaHTMLAttributes, forwardRef } from "react";

interface FieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, FieldProps>(function Textarea(
  { label, hint, id, name, className = "", ...props },
  ref,
) {
  const fieldId = id ?? name ?? label.toLowerCase().replace(/\s+/g, "-");
  const hintId = hint ? `${fieldId}-hint` : undefined;
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink">{label}</label>
      {hint && <p id={hintId} className="mb-1.5 text-xs text-ink/60">{hint}</p>}
      <textarea
        ref={ref}
        id={fieldId}
        name={name}
        rows={4}
        aria-describedby={hintId}
        className={`w-full rounded-[3px] border border-rule bg-white px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(18,32,58,0.04)]
          transition-colors duration-150 placeholder:text-ink/35 hover:border-teal/40
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber focus-visible:border-amber/60 ${className}`}
        {...props}
      />
    </div>
  );
});
