import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";
import Link from "next/link";
import SupportLink from "@/components/SupportLink";
import "./globals.css";

const nunito = Nunito({ variable: "--font-nunito", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Anthem",
  description: "A personal, uplifting song written just for you.",
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
      <body className={`${nunito.variable} min-h-dvh antialiased`}>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2"
        >
          Skip to content
        </a>
        <header className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-4">
          <Link href="/" className="flex items-center gap-2 text-lg font-extrabold tracking-tight text-ink">
            <span aria-hidden className="grid h-8 w-8 place-items-center rounded-full bg-primary-soft text-primary">
              ♪
            </span>
            Anthem
          </Link>
          <SupportLink />
        </header>
        <main id="main" className="mx-auto max-w-3xl px-4 pb-16">
          {children}
        </main>
        <footer className="mx-auto max-w-3xl px-4 pb-10 text-sm text-muted">
          Anthem is a wellbeing tool, not a replacement for therapy or medical care. In an emergency, call 911.
        </footer>
      </body>
    </html>
  );
}
