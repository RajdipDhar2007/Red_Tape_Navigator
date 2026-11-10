import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import VerifyEmail from "@/components/VerifyEmail";

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
