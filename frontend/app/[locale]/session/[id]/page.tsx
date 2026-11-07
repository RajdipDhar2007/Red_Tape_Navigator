import { setRequestLocale } from "next-intl/server";
import SessionView from "@/components/SessionView";

export default async function Page({ params }: { params: Promise<{ locale: string; id: string }> }) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  return <SessionView id={id} />;
}
