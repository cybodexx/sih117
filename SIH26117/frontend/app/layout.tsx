import type { Metadata } from "next";
import { MotionConfig } from "framer-motion";
import "./globals.css";

export const metadata: Metadata = {
  title: "AEGIS-WB — Operational AI Infrastructure",
  description:
    "Air-gapped Enterprise Grounded Inference System — Industrial AI Workbench",
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className="dark">
      <body className="font-sans antialiased">
        <div
          aria-hidden
          className="grain pointer-events-none fixed inset-0 z-[100] opacity-[0.035]"
        />
        <MotionConfig reducedMotion="user">{children}</MotionConfig>
      </body>
    </html>
  );
}