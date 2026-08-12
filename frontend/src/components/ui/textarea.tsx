import { type TextareaHTMLAttributes, forwardRef } from "react";

interface FieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, FieldProps>(function Textarea(
  { label, id, name, className = "", ...props },
  ref,
) {
  const fieldId = id ?? name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink">{label}</label>
      <textarea
        ref={ref}
        id={fieldId}
        name={name}
        rows={4}
        className={`w-full rounded-[3px] border border-rule bg-white px-3 py-2 text-sm text-ink shadow-[inset_0_1px_2px_rgba(18,32,58,0.04)]
          transition-colors duration-150 placeholder:text-ink/35 hover:border-teal/40
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber focus-visible:border-amber/60 ${className}`}
        {...props}
      />
    </div>
  );
});
