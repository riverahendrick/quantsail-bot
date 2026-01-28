"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, List, Info, Menu, X } from "lucide-react";
import { useState } from "react";
import { useTranslations } from "next-intl";

interface PublicShellProps {
  children: React.ReactNode;
}

export function PublicShell({ children }: PublicShellProps) {
  const pathname = usePathname();
  const t = useTranslations("PublicOverview");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { href: "/public/overview", label: t("title"), icon: LayoutDashboard },
    { href: "/public/trades", label: "Trades", icon: List }, // Placeholder translation
    { href: "/public/transparency", label: "Transparency", icon: Info }, // Placeholder translation
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-50 w-full border-b border-border bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        <div className="container flex h-14 items-center px-4 md:px-8">
          <button 
            className="mr-2 md:hidden"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
          
          <div className="flex items-center gap-2 mr-8">
            <span className="text-xl font-bold tracking-tight text-primary">{t("brand")}</span>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "transition-colors hover:text-foreground/80",
                  pathname === item.href ? "text-foreground" : "text-foreground/60"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Mobile Nav Overlay */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-card px-4 py-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsMobileMenuOpen(false)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium",
                pathname === item.href ? "bg-accent text-accent-foreground" : "text-foreground/60"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </div>
      )}

      <main className="flex-1 container px-4 md:px-8 py-6 max-w-7xl mx-auto">
        {children}
      </main>
      
      <footer className="border-t border-border py-6 md:py-0">
         <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row px-4 md:px-8">
            <p className="text-sm text-muted-foreground text-center md:text-left">
               {t("note")}
            </p>
         </div>
      </footer>
    </div>
  );
}
