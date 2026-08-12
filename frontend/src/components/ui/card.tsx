import type { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-[3px] border border-rule bg-white/70 p-5 shadow-[0_1px_2px_rgba(18,32,58,0.06)] ${className}`}
      {...props}
    />
  );
}
