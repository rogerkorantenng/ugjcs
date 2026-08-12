import { type ButtonHTMLAttributes, forwardRef } from "react";
import { Spinner } from "./spinner";

const VARIANTS = {
  primary: "bg-teal text-paper hover:bg-teal-dark disabled:bg-teal/40",
  secondary: "border border-teal/50 bg-transparent text-teal-dark hover:bg-teal/5",
  danger: "bg-brick text-paper hover:bg-brick/90 disabled:bg-brick/40",
} as const;

type Variant = keyof typeof VARIANTS;

/** Shared with anything that must look like a button but can't be one — a `Link` styled as
 * a call-to-action, most often inside an `EmptyState`. Keeps the two visual languages from
 * drifting apart. */
export function buttonClasses(variant: Variant = "primary", className = "") {
  return `inline-flex items-center justify-center gap-2 rounded-[3px] px-4 py-2 text-sm font-medium tracking-wide transition-colors
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber focus-visible:ring-offset-2 focus-visible:ring-offset-paper
    disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`;
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
