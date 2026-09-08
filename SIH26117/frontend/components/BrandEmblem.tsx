"use client";

import { cn } from "@/lib/utils";

const SIZES = {
  sm: "h-6 w-6 rounded-[7px] text-[8px]",
  md: "h-9 w-9 rounded-[11px] text-[11px]",
  lg: "h-14 w-14 rounded-2xl text-base",
} as const;

export function BrandEmblem({
  size = "md",
  className,
}: {
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "pointer-events-none inline-flex select-none items-center justify-center bg-white font-bold tracking-tight text-black shadow-[0_0_24px_rgba(255,255,255,0.28),inset_0_1px_0_rgba(255,255,255,0.9)]",
        SIZES[size],
        className,
      )}
    >
      AE
    </span>
  );
}