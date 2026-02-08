"use client";

import { GridPortfolioWidget } from "@/components/dashboard/grid-portfolio-widget";
import { useTranslations } from "next-intl";
import { Grid3x3, Sparkles } from "lucide-react";

export default function GridPage() {
    const t = useTranslations("GridPage");

    return (
        <div className="space-y-8 max-w-7xl mx-auto">
            {/* Page Header */}
            <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-linear-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                    <Grid3x3 className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        {t("title")}
                        <Sparkles className="w-5 h-5 text-yellow-400" />
                    </h1>
                    <p className="text-sm text-zinc-400">{t("subtitle")}</p>
                </div>
            </div>

            <GridPortfolioWidget />
        </div>
    );
}
