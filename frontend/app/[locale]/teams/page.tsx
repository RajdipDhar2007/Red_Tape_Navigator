import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import TeamsView from "@/components/TeamsView";

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <Suspense>
      <TeamsView />
    </Suspense>
  );
}
