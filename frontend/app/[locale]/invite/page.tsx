import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import AcceptInvite from "@/components/AcceptInvite";

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <Suspense>
      <AcceptInvite />
    </Suspense>
  );
}
