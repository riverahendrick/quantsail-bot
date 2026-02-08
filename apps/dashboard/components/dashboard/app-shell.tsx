"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  LineChart,
  ShieldAlert,
  Settings,
  Activity,
  Users,
  LogOut,
  Menu,
  X,
  Bot,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { auth } from "@/lib/firebase";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const t = useTranslations("Dashboard");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { href: "/app/overview", label: t("overviewTitle"), icon: LayoutDashboard },
    { href: "/app/strategy", label: t("navStrategy"), icon: LineChart },
    { href: "/app/risk", label: t("navRisk"), icon: ShieldAlert },
    { href: "/app/exchange", label: t("navExchange"), icon: Settings },
    { href: "/app/events", label: t("navEvents"), icon: Activity },
    { href: "/app/users", label: t("navUsers"), icon: Users },
    { href: "/app/settings", label: t("navSettings"), icon: Settings },
  ];

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-300 ease-out md:relative md:translate-x-0",
        "glass-strong border-r border-white/10",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Logo Section */}
        <div className="flex h-20 items-center justify-between px-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold text-white tracking-tight">{t("brand")}</span>
              <p className="text-xs text-zinc-500">{t("tradingSystem")}</p>
            </div>
          </div>
          <button
            className="md:hidden p-2 rounded-lg hover:bg-white/10 transition-colors"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <X className="h-5 w-5 text-zinc-400" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col space-y-1 p-4">
          <p className="px-3 py-2 text-xs font-medium text-zinc-500 uppercase tracking-wider">
            {t("mainMenu")}
          </p>

          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-linear-to-r from-cyan-500/20 to-blue-500/10 text-cyan-400 border border-cyan-500/20"
                    : "text-zinc-400 hover:bg-white/5 hover:text-white"
                )}
              >
                <item.icon className={cn(
                  "h-5 w-5 transition-colors",
                  isActive ? "text-cyan-400" : "text-zinc-500 group-hover:text-zinc-300"
                )} />
                <span className="flex-1">{item.label}</span>
                {isActive && (
                  <ChevronRight className="w-4 h-4 text-cyan-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Section */}
        <div className="absolute bottom-0 left-0 w-full p-4 border-t border-white/10">
          {/* User Info Placeholder */}
          <div className="flex items-center gap-3 px-3 py-3 mb-3 rounded-xl bg-white/3">
            <div className="w-9 h-9 rounded-full bg-linear-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <span className="text-sm font-bold text-white">{t("adminUser").charAt(0)}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{t("adminUser")}</p>
              <p className="text-xs text-zinc-500">{t("operator")}</p>
            </div>
          </div>

          {/* Sign Out Button */}
          <button
            onClick={() => auth.signOut()}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-zinc-400 transition-all hover:bg-rose-500/10 hover:text-rose-400 group"
          >
            <LogOut className="h-5 w-5 transition-colors" />
            <span>{t("signOut")}</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {/* Mobile Header */}
        <header className="flex h-20 items-center justify-between border-b border-white/10 bg-background/50 backdrop-blur-xl px-4 md:hidden">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-linear-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-white">{t("brand")}</span>
          </div>
          <button
            onClick={() => setIsMobileMenuOpen(true)}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <Menu className="h-6 w-6 text-zinc-400" />
          </button>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
