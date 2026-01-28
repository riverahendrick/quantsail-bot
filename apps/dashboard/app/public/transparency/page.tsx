"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";

export default function PublicTransparencyPage() {
  const t = useTranslations("PublicTransparency");

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      <div className="flex flex-col gap-2">
         <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
         <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle>{t("pipelineTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p dangerouslySetInnerHTML={{ __html: t.raw("pipelineDesc").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
            <ul className="list-disc pl-5 space-y-1">
               <li dangerouslySetInnerHTML={{ __html: t.raw("voteAgg").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
               <li dangerouslySetInnerHTML={{ __html: t.raw("confScore").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
               <li dangerouslySetInnerHTML={{ __html: t.raw("riskGates").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
            </ul>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
           <CardHeader>
             <CardTitle>{t("safetyTitle")}</CardTitle>
           </CardHeader>
           <CardContent className="space-y-4 text-sm text-muted-foreground">
             <p>{t("safetyDesc")}</p>
             <ul className="list-disc pl-5 space-y-1">
                <li dangerouslySetInnerHTML={{ __html: t.raw("circuitBreakers").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
                <li dangerouslySetInnerHTML={{ __html: t.raw("newsEvents").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
                <li dangerouslySetInnerHTML={{ __html: t.raw("dailyLock").replace(/\{b\}/g, "<strong>").replace(/\{\/b\}/g, "</strong>") }} />
             </ul>
           </CardContent>
        </Card>
        
        <Card className="border-border bg-card md:col-span-2">
           <CardHeader>
             <CardTitle>{t("privacyTitle")}</CardTitle>
           </CardHeader>
           <CardContent className="space-y-4 text-sm text-muted-foreground">
             <p>{t("privacyDesc")}</p>
             <div className="rounded-md bg-secondary p-4">
                <h4 className="font-bold text-foreground mb-2">{t("hiddenTitle")}</h4>
                <ul className="list-disc pl-5 space-y-1">
                   <li>{t("hidden1")}</li>
                   <li>{t("hidden2")}</li>
                   <li>{t("hidden3")}</li>
                   <li>{t("hidden4")}</li>
                </ul>
             </div>
           </CardContent>
        </Card>
      </div>
    </div>
  );
}