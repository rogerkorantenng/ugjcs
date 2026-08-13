import { type ButtonHTMLAttributes, forwardRef } from "react";
import { Spinner } from "./spinner";

// `danger` is visually a different object from `primary`/`secondary`, not just a red
// recolour of the same shape: a heavier weight and a diagonal-hazard texture (the same
// device the redaction bar uses) so a destructive action reads as categorically different
// at a glance, not merely differently coloured.
const VARIANTS = {
  primary: "bg-stamp text-paper shadow-sm hover:bg-stamp-dark hover:shadow disabled:bg-stamp/40 disabled:shadow-none",
  secondary: "border border-stamp/40 bg-transparent text-stamp hover:border-stamp hover:bg-stamp/5",
  danger:
    "border-2 border-seal bg-seal text-paper shadow-sm hover:bg-seal/90 hover:shadow disabled:bg-seal/40 disabled:border-seal/40 disabled:shadow-none",
} as const;

type Variant = keyof typeof VARIANTS;

/** Shared with anything that must look like a button but can't be one — a `Link` styled as
 * a call-to-action, most often inside an `EmptyState`. Keeps the two visual languages from
 * drifting apart. */
export function buttonClasses(variant: Variant = "primary", className = "") {
  return `inline-flex items-center justify-center gap-2 rounded-[3px] px-4 py-2 text-sm font-semibold tracking-wide
    transition-all duration-150 ease-out active:scale-[0.97]
    focus-visible:outline-2 focus-visible:outline-offset-2
    disabled:cursor-not-allowed disabled:active:scale-100 ${VARIANTS[variant]} ${className}`;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  /** Disables the button, sets `aria-busy`, and shows a spinner — the one flag a submit
   * handler needs to set to make an in-flight request visible and to make a double-click
   * impossible. */
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", isLoading = false, disabled, className = "", children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={buttonClasses(variant, className)}
      {...props}
    >
      {isLoading && <Spinner />}
      {children}
    </button>
  );
});
