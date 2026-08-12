import { type ButtonHTMLAttributes, forwardRef } from "react";

const VARIANTS = {
  primary: "bg-teal text-paper hover:bg-teal-dark disabled:bg-teal/40",
  secondary: "border border-teal/50 bg-transparent text-teal-dark hover:bg-teal/5",
  danger: "bg-brick text-paper hover:bg-brick/90 disabled:bg-brick/40",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANTS;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", className = "", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`rounded-[3px] px-4 py-2 text-sm font-medium tracking-wide transition-colors
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber focus-visible:ring-offset-2 focus-visible:ring-offset-paper
        disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
});
