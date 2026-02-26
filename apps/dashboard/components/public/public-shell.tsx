"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, List, Info, Menu, X, Bot, ExternalLink, Github, Twitter } from "lucide-react";
import { useState } from "react";
import { useTranslations } from "next-intl";

interface PublicShellProps {
  children: React.ReactNode;
}

export function PublicShell({ children }: PublicShellProps) {
  const pathname = usePathname();
  const t = useTranslations("PublicOverview");
  const tCommon = useTranslations("Common");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { href: "/public/overview", label: t("title"), icon: LayoutDashboard },
    { href: "/public/trades", label: t("trades"), icon: List },
    { href: "/public/transparency", label: t("transparency"), icon: Info },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full glass-strong border-b border-white/10">
        <div className="container flex h-20 items-center px-4 md:px-8">
          {/* Mobile Menu Button */}
          <button
            className="mr-4 md:hidden p-2 rounded-lg hover:bg-white/10 transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-6 w-6 text-zinc-400" /> : <Menu className="h-6 w-6 text-zinc-400" />}
          </button>

          {/* Logo */}
          <Link href="/public/overview" className="flex items-center gap-3 mr-8 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 group-hover:shadow-cyan-500/30 transition-shadow">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div className="hidden sm:block">
              <span className="text-xl font-bold tracking-tight text-white">{t("brand")}</span>
              <p className="text-xs text-zinc-500">{t("transparencyDashboard")}</p>
            </div>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200",
                  pathname === item.href
                    ? "bg-white/10 text-white"
                    : "text-zinc-400 hover:text-white hover:bg-white/5"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Right Side Actions */}
          <div className="flex items-center gap-3 ml-auto">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-zinc-400 hover:text-white hover:bg-white/5 transition-all"
            >
              <Github className="h-4 w-4" />
              <span>{t("github")}</span>
            </a>
            <a
              href="/app/overview"
              className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
            >
              <span>{t("operatorLogin")}</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
            <a
              href="/app/overview"
              className="sm:hidden flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
            >
              <span>{t("login")}</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </header>

      {/* Mobile Nav Overlay */}
      {isMobileMenuOpen && (
        <div className="md:hidden glass-strong border-b border-white/10 px-4 py-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsMobileMenuOpen(false)}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all",
                pathname === item.href
                  ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-400 border border-cyan-500/20"
                  : "text-zinc-400 hover:bg-white/5 hover:text-white"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </Link>
          ))}

          <div className="pt-4 mt-4 border-t border-white/10 space-y-2">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-zinc-400 hover:bg-white/5 hover:text-white transition-all"
            >
              <Github className="h-5 w-5" />
              {t("github")}
            </a>
            <a
              href="/app/overview"
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
            >
              <ExternalLink className="h-4 w-4" />
              {t("operatorLogin")}
            </a>
            <a
              href="https://twitter.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-zinc-400 hover:bg-white/5 hover:text-white transition-all"
            >
              <Twitter className="h-5 w-5" />
              {t("twitter")}
            </a>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 container px-4 md:px-8 py-8 max-w-7xl mx-auto">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 glass">
        <div className="container flex flex-col md:flex-row items-center justify-between gap-4 py-8 px-4 md:px-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/50 to-blue-600/50 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">{t("brand")}</p>
              <p className="text-xs text-zinc-500">{t("tagline")}</p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <a href="#" className="text-sm text-zinc-500 hover:text-white transition-colors">{t("docs")}</a>
            <a href="#" className="text-sm text-zinc-500 hover:text-white transition-colors">{t("api")}</a>
            <a href="#" className="text-sm text-zinc-500 hover:text-white transition-colors">{t("status")}</a>
          </div>

          <p className="text-sm text-zinc-600 text-center md:text-right">
            {t("note")} {tCommon("separator")} <a href="/app/overview" className="text-zinc-700 hover:text-zinc-500 transition-colors">{t("login")}</a>
          </p>
        </div>
      </footer>
    </div>
  );
}
