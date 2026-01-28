"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { useTranslations } from "next-intl";

interface GlowCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "primary" | "success" | "warning" | "destructive" | "purple";
  glowOnHover?: boolean;
  gradientBorder?: boolean;
  children: React.ReactNode;
}

export function GlowCard({
  className,
  variant = "default",
  glowOnHover = true,
  gradientBorder = false,
  children,
  ...props
}: GlowCardProps) {
  const variantClasses = {
    default: "",
    primary: "hover:shadow-[0_0_30px_-5px_rgba(6,182,212,0.3)]",
    success: "hover:shadow-[0_0_30px_-5px_rgba(16,185,129,0.3)]",
    warning: "hover:shadow-[0_0_30px_-5px_rgba(245,158,11,0.3)]",
    destructive: "hover:shadow-[0_0_30px_-5px_rgba(244,63,94,0.3)]",
    purple: "hover:shadow-[0_0_30px_-5px_rgba(139,92,246,0.3)]",
  };

  return (
    <div
      className={cn(
        "relative rounded-xl overflow-hidden",
        "bg-gradient-to-br from-white/[0.05] to-white/[0.02]",
        "backdrop-blur-xl",
        "border border-white/[0.08]",
        "transition-all duration-300 ease-out",
        "hover:border-white/[0.15]",
        "hover:-translate-y-0.5",
        glowOnHover && variantClasses[variant],
        className
      )}
      {...props}
    >
      {/* Gradient border overlay */}
      {gradientBorder && (
        <div 
          className="absolute inset-0 rounded-xl pointer-events-none"
          style={{
            background: "linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.1) 100%)",
            mask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
            maskComposite: "xor",
            WebkitMaskComposite: "xor",
            padding: "1px",
          }}
        />
      )}
      
      {/* Inner highlight */}
      <div className="absolute inset-0 rounded-xl pointer-events-none bg-gradient-to-b from-white/[0.05] to-transparent" />
      
      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}

// Metric Card Component
interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  trend?: {
    value: number;
    label: string;
  };
  variant?: "default" | "primary" | "success" | "warning" | "destructive" | "purple";
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = "default",
  className,
  ...props
}: MetricCardProps) {
  const tCommon = useTranslations("Common");
  const variantColors = {
    default: {
      iconBg: "bg-white/10",
      iconColor: "text-white",
      glow: "",
    },
    primary: {
      iconBg: "bg-cyan-500/20",
      iconColor: "text-cyan-400",
      glow: "group-hover:shadow-[0_0_30px_-5px_rgba(6,182,212,0.4)]",
    },
    success: {
      iconBg: "bg-emerald-500/20",
      iconColor: "text-emerald-400",
      glow: "group-hover:shadow-[0_0_30px_-5px_rgba(16,185,129,0.4)]",
    },
    warning: {
      iconBg: "bg-amber-500/20",
      iconColor: "text-amber-400",
      glow: "group-hover:shadow-[0_0_30px_-5px_rgba(245,158,11,0.4)]",
    },
    destructive: {
      iconBg: "bg-rose-500/20",
      iconColor: "text-rose-400",
      glow: "group-hover:shadow-[0_0_30px_-5px_rgba(244,63,94,0.4)]",
    },
    purple: {
      iconBg: "bg-violet-500/20",
      iconColor: "text-violet-400",
      glow: "group-hover:shadow-[0_0_30px_-5px_rgba(139,92,246,0.4)]",
    },
  };

  const colors = variantColors[variant];

  return (
    <GlowCard
      variant={variant}
      className={cn("group", className)}
      {...props}
    >
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-3">
            <p className="text-sm font-medium text-zinc-400">{title}</p>
            <div className="space-y-1">
              <p className="text-3xl font-bold tracking-tight text-white number-display">
                {value}
              </p>
              {subtitle && (
                <p className="text-xs text-zinc-500">{subtitle}</p>
              )}
            </div>
            {trend && (
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "text-xs font-medium px-2 py-0.5 rounded-full",
                    trend.value >= 0
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-rose-500/20 text-rose-400"
                  )}
                >
                  {trend.value >= 0 ? tCommon("plus") : ""}
                  {trend.value}{tCommon("percent")}
                </span>
                <span className="text-xs text-zinc-500">{trend.label}</span>
              </div>
            )}
          </div>
          <div
            className={cn(
              "p-3 rounded-xl transition-all duration-300",
              colors.iconBg,
              colors.iconColor,
              colors.glow
            )}
          >
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </div>
    </GlowCard>
  );
}
