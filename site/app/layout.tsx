import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME, SITE_TAGLINE, siteUrl } from "@/lib/content";
import { SPONSOR, sponsorUrl } from "@/lib/sponsor";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: {
    default: `${SITE_NAME} — search trend briefings you can verify`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_TAGLINE,
  alternates: {
    canonical: "/",
    types: { "application/rss+xml": "/feed.xml" },
  },
  openGraph: {
    siteName: SITE_NAME,
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="container">
            <Link href="/" className="brand">
              TrendFlow<span> Briefings</span>
            </Link>
            <nav className="nav">
              <Link href="/">Briefings</Link>
              <Link href="/ai-infrastructure">AI Infrastructure</Link>
              <Link href="/about">Editorial policy</Link>
              <Link href="/feed.xml">RSS</Link>
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="site-footer">
          <div className="container">
            <div>
              © {new Date().getFullYear()} {SITE_NAME}. Sources are cited on every
              briefing; see our <Link href="/about">editorial &amp; AI policy</Link>.
            </div>
            <div>
              <Link href="/privacy">Privacy</Link>
            </div>
          </div>
          <div className="container footer-sponsor" data-testid="footer-sponsor">
            Sponsored (affiliated):{" "}
            <a href={sponsorUrl("footer")} rel="sponsored noopener" target="_blank">
              {SPONSOR.name}
            </a>{" "}
            — {SPONSOR.tagline}. See our{" "}
            <Link href="/about#advertising">advertising disclosure</Link>.
          </div>
        </footer>
      </body>
    </html>
  );
}
