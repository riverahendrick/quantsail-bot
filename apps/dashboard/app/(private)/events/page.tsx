"use client";

import { useEffect, useState } from "react";
import { getPrivateEvents } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { GlowCard } from "@/components/ui/glow-card";
import { Button } from "@/components/ui/button";
import { RefreshCw, List } from "lucide-react";
import { useTranslations } from "next-intl";

type SystemEvent = {
  id: string;
  seq: number;
  ts: string;
  level: string;
  type: string;
  symbol: string | null;
  payload: Record<string, unknown>;
};

export default function EventsPage() {
  const t = useTranslations("EventsPage");
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPrivateEvents();
      // Client-side sort by seq descending just in case
      setEvents((data as SystemEvent[]).sort((a, b) => b.seq - a.seq));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load events";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <Button variant="outline" size="icon" onClick={fetchEvents} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <GlowCard variant="default">
        <div className="p-6 border-b border-white/5">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <List className="h-5 w-5 text-cyan-400" />
            {t("systemEventsTitle")}
          </h3>
        </div>
        <div className="p-6">
            {error && <div className="p-4 mb-4 text-red-500 border border-red-200 rounded">{error}</div>}
            
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>{t("time")}</TableHead>
                        <TableHead>{t("seq")}</TableHead>
                        <TableHead>{t("level")}</TableHead>
                        <TableHead>{t("type")}</TableHead>
                        <TableHead>{t("symbol")}</TableHead>
                        <TableHead>{t("payload")}</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {events.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={6} className="text-center text-muted-foreground h-24">
                                {loading ? t("loading") : t("noEvents")}
                            </TableCell>
                        </TableRow>
                    ) : (
                        events.map((event) => (
                            <TableRow key={event.id || event.seq}>
                                <TableCell className="whitespace-nowrap font-mono text-xs">
                                    {new Date(event.ts).toLocaleTimeString()}
                                </TableCell>
                                <TableCell className="font-mono text-xs text-muted-foreground">
                                    {event.seq}
                                </TableCell>
                                <TableCell>
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                        event.level === "ERROR" ? "bg-rose-500/20 text-rose-400 border border-rose-500/30" :
                                        event.level === "WARN" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" :
                                        "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                    }`}>
                                        {event.level}
                                    </span>
                                </TableCell>
                                <TableCell className="font-medium text-xs">
                                    {event.type}
                                </TableCell>
                                <TableCell className="text-xs">
                                    {event.symbol || "-"}
                                </TableCell>
                                <TableCell className="font-mono text-xs max-w-[300px] truncate" title={JSON.stringify(event.payload, null, 2)}>
                                    {JSON.stringify(event.payload)}
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        </div>
      </GlowCard>
    </div>
  );
}