import { useDashboardStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { AlertOctagon, CheckCircle2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export function BreakersWidget() {
  const { botState } = useDashboardStore();
  const t = useTranslations("Dashboard");
  const breakers = botState.active_breakers;

  return (
    <Card className="col-span-1 md:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base font-medium">{t("activeBreakers")}</CardTitle>
        {breakers.length > 0 ? (
          <AlertOctagon className="h-4 w-4 text-red-500" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        )}
      </CardHeader>
      <CardContent>
        {breakers.length === 0 ? (
          <div className="flex h-20 items-center justify-center text-sm text-muted-foreground">
            {t("noActiveBreakers")}
          </div>
        ) : (
          <ul className="space-y-3">
            {breakers.map((breaker, idx) => (
              <li key={idx} className="flex items-center justify-between rounded-md border p-2 text-sm">
                <span className="font-medium text-red-600 dark:text-red-400">
                  {breaker.type}
                </span>
                {breaker.expiry && (
                  <span className="text-muted-foreground">
                    {t("expiresIn")} {formatDistanceToNow(new Date(breaker.expiry))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
