import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";
import Link from "next/link";
import Logo from "@/components/Logo";
import SupportLink from "@/components/SupportLink";
import "./globals.css";

const nunito = Nunito({ variable: "--font-nunito", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Echorie",
  description: "A personal, uplifting song made just for you.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f4ef" },
    { media: "(prefers-color-scheme: dark)", color: "#141a1d" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${nunito.variable} flex min-h-dvh flex-col antialiased`}>
        <div className="ambient" aria-hidden />
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2"
        >
          Skip to content
        </a>
        <header className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-5">
          <Link href="/" aria-label="Echorie home" className="text-ink">
            <Logo />
          </Link>
          <SupportLink />
        </header>
        <main id="main" className="mx-auto w-full max-w-3xl flex-1 px-4 pb-16">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-3xl px-4 pb-8 text-center text-xs text-muted">
          Not a substitute for professional care · In an emergency, call 911
        </footer>
      </body>
    </html>
  );
}
