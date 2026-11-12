import { setRequestLocale } from "next-intl/server";
import HelpView from "@/components/HelpView";

export default async function HelpPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <HelpView />;
}

