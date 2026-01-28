"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";
import { useTranslations } from "next-intl";

// Neo Card Variants - Enhanced glassmorphism with neon accents
const neoCardVariants = cva(
  "relative rounded-2xl overflow-hidden backdrop-blur-xl transition-all duration-300",
  {
    variants: {
      variant: {
        default: [
          "bg-gradient-to-br from-white/[0.08] to-white/[0.02]",
          "border border-white/[0.08]",
          "hover:border-white/[0.15]",
          "hover:shadow-[0_8px_32px_-8px_rgba(6,182,212,0.15)]",
        ],
        primary: [
          "bg-gradient-to-br from-cyan-500/10 to-blue-500/5",
          "border border-cyan-500/20",
          "hover:border-cyan-500/30",
          "hover:shadow-[0_8px_32px_-8px_rgba(6,182,212,0.25)]",
        ],
        success: [
          "bg-gradient-to-br from-emerald-500/10 to-emerald-500/5",
          "border border-emerald-500/20",
          "hover:border-emerald-500/30",
          "hover:shadow-[0_8px_32px_-8px_rgba(16,185,129,0.25)]",
        ],
        warning: [
          "bg-gradient-to-br from-amber-500/10 to-orange-500/5",
          "border border-amber-500/20",
          "hover:border-amber-500/30",
          "hover:shadow-[0_8px_32px_-8px_rgba(245,158,11,0.25)]",
        ],
        destructive: [
          "bg-gradient-to-br from-rose-500/10 to-red-500/5",
          "border border-rose-500/20",
          "hover:border-rose-500/30",
          "hover:shadow-[0_8px_32px_-8px_rgba(244,63,94,0.25)]",
        ],
        purple: [
          "bg-gradient-to-br from-violet-500/10 to-purple-500/5",
          "border border-violet-500/20",
          "hover:border-violet-500/30",
          "hover:shadow-[0_8px_32px_-8px_rgba(139,92,246,0.25)]",
        ],
        glow: [
          "bg-gradient-to-br from-white/[0.05] to-white/[0.01]",
          "border border-white/[0.1]",
          "shadow-[0_0_40px_-10px_rgba(6,182,212,0.2)]",
          "hover:shadow-[0_0_60px_-10px_rgba(6,182,212,0.35)]",
        ],
      },
      size: {
        default: "",
        sm: "rounded-xl",
        lg: "rounded-3xl",
      },
      interactive: {
        true: "cursor-pointer hover:-translate-y-1 active:translate-y-0",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      interactive: false,
    },
  }
);

export interface NeoCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof neoCardVariants> {
  children: React.ReactNode;
  gradientBorder?: boolean;
  shimmer?: boolean;
}

// Main Neo Card Component
export function NeoCard({
  className,
  variant,
  size,
  interactive,
  gradientBorder = false,
  children,
  ...props
}: NeoCardProps) {
  return (
    <div
      className={cn(
        neoCardVariants({ variant, size, interactive }),
        "group",
        className
      )}
      {...props}
    >
      {/* Gradient Border Overlay */}
      {gradientBorder && (
        <div
          className="absolute inset-0 rounded-2xl pointer-events-none p-[1px]"
          style={{
            background: "linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.05) 50%, rgba(6,182,212,0.15) 100%)",
            mask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
            maskComposite: "xor",
            WebkitMaskComposite: "xor",
          }}
        />
      )}

      {/* Inner Highlight Gradient */}
      <div className="absolute inset-0 rounded-2xl pointer-events-none bg-gradient-to-b from-white/[0.08] to-transparent opacity-50" />

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}

// Neo Metric Card - For KPI displays
interface NeoMetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  trend?: {
    value: number;
    label: string;
  };
  variant?: "default" | "primary" | "success" | "warning" | "destructive" | "purple";
  size?: "default" | "lg";
}

export function NeoMetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = "default",
  size = "default",
  className,
  ...props
}: NeoMetricCardProps) {
  const tCommon = useTranslations("Common");
  const variantStyles = {
    default: {
      iconBg: "bg-white/10",
      iconColor: "text-white",
    },
    primary: {
      iconBg: "bg-cyan-500/20",
      iconColor: "text-cyan-400",
    },
    success: {
      iconBg: "bg-emerald-500/20",
      iconColor: "text-emerald-400",
    },
    warning: {
      iconBg: "bg-amber-500/20",
      iconColor: "text-amber-400",
    },
    destructive: {
      iconBg: "bg-rose-500/20",
      iconColor: "text-rose-400",
    },
    purple: {
      iconBg: "bg-violet-500/20",
      iconColor: "text-violet-400",
    },
  };

  const styles = variantStyles[variant];

  return (
    <NeoCard
      variant={variant}
      interactive
      className={cn("group", className)}
      {...props}
    >
      <div className={cn("p-6", size === "lg" && "p-8")}>
        <div className="flex items-start justify-between">
          <div className="space-y-3">
            <p className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
              {title}
            </p>
            <div className="space-y-1">
              <p className={cn("font-bold tracking-tight text-white number-display", size === "lg" ? "text-4xl" : "text-3xl")}>
                {value}
              </p>
              {subtitle && <p className="text-xs text-zinc-500">{subtitle}</p>}
            </div>
            {/* Trend section - always reserve space for consistent height */}
            <div className="h-7 flex items-center">
              {trend ? (
                <div className="flex items-center gap-2">
                  <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full", trend.value >= 0 ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30")}>
                    {trend.value >= 0 ? tCommon("plus") : ""}{trend.value}{tCommon("percent")}
                  </span>
                  <span className="text-xs text-zinc-500">{trend.label}</span>
                </div>
              ) : (
                /* Spacer to maintain height when no trend */
                <span className="text-xs text-zinc-600">{tCommon("spacer")}</span>
              )}
            </div>
          </div>
          <div className={cn("p-3 rounded-xl transition-all duration-300 shadow-lg", styles.iconBg, styles.iconColor)}>
            <Icon className={cn("transition-transform group-hover:scale-110", size === "lg" ? "w-7 h-7" : "w-6 h-6")} />
          </div>
        </div>
      </div>
    </NeoCard>
  );
}

// Neo Status Card - For status displays
interface NeoStatusCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  status: "online" | "offline" | "warning" | "error";
  message?: string;
}

export function NeoStatusCard({
  title,
  status,
  message,
  className,
  ...props
}: NeoStatusCardProps) {
  const t = useTranslations("Dashboard");
  const statusConfig = {
    online: {
      bg: "from-emerald-500/10 to-emerald-500/5",
      border: "border-emerald-500/20",
      dot: "bg-emerald-400",
      text: "text-emerald-400",
      label: t("online"),
    },
    offline: {
      bg: "from-zinc-500/10 to-zinc-500/5",
      border: "border-zinc-500/20",
      dot: "bg-zinc-400",
      text: "text-zinc-400",
      label: t("offline"),
    },
    warning: {
      bg: "from-amber-500/10 to-amber-500/5",
      border: "border-amber-500/20",
      dot: "bg-amber-400",
      text: "text-amber-400",
      label: t("warning"),
    },
    error: {
      bg: "from-rose-500/10 to-rose-500/5",
      border: "border-rose-500/20",
      dot: "bg-rose-400",
      text: "text-rose-400",
      label: t("error"),
    },
  };

  const config = statusConfig[status];

  return (
    <NeoCard className={cn("overflow-hidden", className)} {...props}>
      <div className={cn("p-5 bg-gradient-to-br", config.bg)}>
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className={cn("w-3 h-3 rounded-full", config.dot, status === "online" && "animate-pulse")} />
            {status === "online" && (
              <>
                <span className="absolute inset-0 rounded-full animate-ping opacity-40 bg-emerald-400" />
                <span className="absolute -inset-1 rounded-full animate-ping opacity-20 bg-emerald-400" style={{ animationDelay: "0.2s" }} />
              </>
            )}
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-400">{title}</p>
            <p className={cn("text-lg font-semibold", config.text)}>{config.label}</p>
          </div>
          {message && <p className="ml-auto text-sm text-zinc-500">{message}</p>}
        </div>
      </div>
    </NeoCard>
  );
}
