"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { AlertTriangle, Lock, ShieldCheck } from "lucide-react";
import { DASHBOARD_CONFIG } from "@/lib/config";
import { useTranslations } from "next-intl";
import { auth } from "@/lib/firebase";

export function ArmingModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState<"IDLE" | "ARMED" | "LIVE">("IDLE");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const t = useTranslations("Dashboard");

  const handleArm = async () => {
    setLoading(true);
    setError("");
    try {
      if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
        setToken("mock-token-123");
        setStep("ARMED");
        setLoading(false);
        return;
      }

      const user = auth.currentUser;
      const idToken = user ? await user.getIdToken() : "";
      
      const res = await fetch(`${DASHBOARD_CONFIG.API_URL}/v1/bot/arm`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${idToken}` }
      });
      
      if (!res.ok) throw new Error("Failed to arm system");
      
      const data = await res.json();
      setToken(data.arming_token);
      setStep("ARMED");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Arming failed");
    } finally {
      setLoading(false);
    }
  };

  const handleStartLive = async () => {
    setLoading(true);
    setError("");
    try {
      if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
        setStep("LIVE");
        setLoading(false);
        setTimeout(() => setIsOpen(false), 2000);
        return;
      }

      const user = auth.currentUser;
      const idToken = user ? await user.getIdToken() : "";

      const res = await fetch(`${DASHBOARD_CONFIG.API_URL}/v1/bot/start`, {
        method: "POST",
        headers: { 
            "Authorization": `Bearer ${idToken}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ mode: "live", arming_token: token })
      });

      if (!res.ok) throw new Error("Failed to start live trading");
      
      setStep("LIVE");
      setTimeout(() => setIsOpen(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Start failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive" className="gap-2">
          <AlertTriangle className="h-4 w-4" />
          {t("armLive")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <ShieldCheck className="h-5 w-5" />
            {t("liveGate")}
          </DialogTitle>
          <DialogDescription>
            {t("liveWarn")}
          </DialogDescription>
        </DialogHeader>
        
        <div className="py-4">
          {step === "IDLE" && (
            <div className="rounded-md bg-yellow-500/10 p-4 border border-yellow-500/20 text-yellow-500 text-sm">
              {t("step1")}
            </div>
          )}
          
          {step === "ARMED" && (
            <div className="rounded-md bg-red-500/10 p-4 border border-red-500/20 text-red-500 text-sm">
              <p className="font-bold flex items-center gap-2">
                <Lock className="h-4 w-4" /> {t("systemArmed")}
              </p>
              <p className="mt-2">{t("tokenAcquired")}</p>
            </div>
          )}

          {step === "LIVE" && (
            <div className="rounded-md bg-green-500/10 p-4 border border-green-500/20 text-green-500 text-sm text-center font-bold">
              {t("liveActive")}
            </div>
          )}

          {error && (
            <div className="mt-4 text-sm text-red-500 font-medium">
              {t("error")} {error}
            </div>
          )}
        </div>

        <DialogFooter>
          {step === "IDLE" && (
            <Button onClick={handleArm} disabled={loading}>
              {loading ? t("arming") : t("requestToken")}
            </Button>
          )}
          {step === "ARMED" && (
            <Button variant="destructive" onClick={handleStartLive} disabled={loading}>
              {loading ? t("starting") : t("confirmLive")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
