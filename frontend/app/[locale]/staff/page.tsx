import { setRequestLocale } from "next-intl/server";
import StaffConsole from "@/components/StaffConsole";

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <StaffConsole />;
}
