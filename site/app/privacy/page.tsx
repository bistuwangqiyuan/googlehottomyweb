import type { Metadata } from "next";
import { SITE_NAME } from "@/lib/content";

export const metadata: Metadata = {
  title: "Privacy",
  description: `Privacy policy for ${SITE_NAME}.`,
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <div className="prose container">
      <h1>Privacy</h1>
      <p>
        <strong>{SITE_NAME}</strong> is a static, read-only publication. We keep data
        collection to the minimum required to operate the site.
      </p>
      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>No accounts, no forms, no cookies set by us.</strong> Reading this
          site does not require providing any personal information.
        </li>
        <li>
          <strong>Hosting logs:</strong> our hosting provider (Vercel) processes
          standard technical request data (IP address, user agent) to serve and secure
          the site, per its own privacy policy.
        </li>
      </ul>
      <h2>Third-party links</h2>
      <p>
        Briefings link to external news sources. Their privacy practices are their
        own; we encourage you to review them.
      </p>
      <h2>Changes</h2>
      <p>
        If we ever add analytics or advertising, this page will be updated first, and
        any such tools will be configured in a privacy-respecting way and disclosed
        here.
      </p>
    </div>
  );
}
