import Link from "next/link";

export default function NotFound() {
  return (
    <div className="prose container">
      <h1>Page not found</h1>
      <p>
        This briefing may have been taken down after an editorial review, or the URL
        is incorrect. <Link href="/">Back to all briefings</Link>.
      </p>
    </div>
  );
}
