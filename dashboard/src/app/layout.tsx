import type { Metadata } from "next";
import { Poppins, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "./workspace.css";
import "./ui.css";
import "./warmth.css";
import "./select.css";
import { AuthProvider } from "@/context/AuthContext";
import { I18nProvider } from "@/i18n/I18nProvider";
import { ToastProvider } from "@/components/ui/Toast";
import LanguageSync from "@/components/LanguageSync";
import ExamGate from "@/components/ExamGate";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-poppins-source",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jetbrains-source",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Afferent Reflex: Centralized Security Dashboard",
  description: "Unified security awareness platform combining phishing simulation, threat intelligence, and behavioral risk telemetry.",
  keywords: "cybersecurity, phishing, security awareness, afferent, threat intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${poppins.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <head>
        {/* Apply the saved theme (or the system one when none is saved) before first paint so there is no flash. */}
        <script dangerouslySetInnerHTML={{ __html: "try{var t=localStorage.getItem('hfl_theme');if(t!=='light'&&t!=='dark')t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.setAttribute('data-theme',t)}catch(e){}" }} />
      </head>
      <body className="font-body">
        <I18nProvider>
          <ToastProvider>
            <AuthProvider>
              <LanguageSync />
              <ExamGate />
              {children}
            </AuthProvider>
          </ToastProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
