import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export function formatPct(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 2,
  }).format(value / 100); // Expects value like 1.5 for 1.5%? Or 0.015? 
  // API spec says "pnl_pct" which usually is 10.0 for 10%. Let's assume 0.10 is 10%. 
  // Wait, API spec for `taker_fee_bps` says 10bps = 0.1%.
  // Standardize: if input is 0.10, output 10%.
}
