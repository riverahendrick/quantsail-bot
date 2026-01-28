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
  LogOut,
  Menu,
  X
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
    { href: "/overview", label: t("overviewTitle"), icon: LayoutDashboard },
    { href: "/strategy", label: t("navStrategy"), icon: LineChart },
    { href: "/risk", label: t("navRisk"), icon: ShieldAlert },
    { href: "/exchange", label: t("navExchange"), icon: Settings },
    { href: "/events", label: t("navEvents"), icon: Activity },
  ];

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 transform border-r border-border bg-card transition-transform duration-200 ease-in-out md:relative md:translate-x-0",
        isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex h-16 items-center justify-between px-6 border-b border-border">
          <span className="text-lg font-bold tracking-tight text-primary">{t("brand")}</span>
          <button 
            className="md:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="flex flex-col space-y-1 p-4">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
                  isActive ? "bg-accent text-primary" : "text-muted-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        
        <div className="absolute bottom-4 left-0 w-full px-4">
          <button 
            onClick={() => auth.signOut()}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          >
            <LogOut className="h-4 w-4" />
            {t("signOut")}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        {/* Mobile Header */}
        <header className="flex h-16 items-center border-b border-border bg-card px-4 md:hidden">
           <button onClick={() => setIsMobileMenuOpen(true)}>
             <Menu className="h-6 w-6" />
           </button>
           <span className="ml-4 font-bold">{t("brand")}</span>
        </header>
        
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
