import type { Metadata } from "next";
import { Suspense } from "react";
import { Inter, Noto_Sans_Devanagari } from "next/font/google";
import { AuthProvider } from "@/components/AuthProvider";
import { Footer, Header, TrustBar } from "@/components/Header";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-devanagari",
  subsets: ["devanagari"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "IndiaJob.in — Government Jobs & Sarkari Naukri Notifications",
  description:
    "Daily government job alerts from UPSC, SSC, RRB, IBPS, State PSC and Employment News. Vacancies, eligibility, last dates and official apply links — updated daily.",
  keywords: [
    "government jobs",
    "sarkari naukri",
    "job alert",
    "UPSC recruitment",
    "SSC jobs",
    "RRB notification",
    "IBPS clerk",
    "state PSC",
    "vacancy notification",
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-IN" className={`${inter.variable} ${notoDevanagari.variable} h-full scroll-smooth`}>
      <body className="min-h-full flex flex-col antialiased">
        <AuthProvider>
          <TrustBar />
          <Suspense fallback={<div className="h-14 border-b border-slate-200 bg-white" />}>
            <Header />
          </Suspense>
          <main className="flex-1">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
