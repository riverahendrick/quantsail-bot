"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { defaultLocale, isLocale, localeCookieName } from "@/i18n/locales";

export async function setLocale(locale: string, redirectTo: string) {
  const resolvedLocale = isLocale(locale) ? locale : defaultLocale;
  const cookieStore = await cookies();

  cookieStore.set(localeCookieName, resolvedLocale, { path: "/" });
  redirect(redirectTo);
}
