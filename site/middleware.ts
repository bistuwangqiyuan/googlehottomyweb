import { NextRequest, NextResponse } from "next/server";

// /admin 抽检后台的 Basic Auth。未配置凭据时 fail-closed（拒绝访问并说明原因）。
export function middleware(req: NextRequest) {
  const user = process.env.ADMIN_USER;
  const pass = process.env.ADMIN_PASS;

  if (!user || !pass) {
    return new NextResponse(
      "Admin area is disabled: set ADMIN_USER and ADMIN_PASS environment variables to enable it.",
      { status: 503 }
    );
  }

  const auth = req.headers.get("authorization");
  if (auth?.startsWith("Basic ")) {
    try {
      const [u, p] = atob(auth.slice(6)).split(":");
      if (u === user && p === pass) return NextResponse.next();
    } catch {
      // fall through to 401
    }
  }
  return new NextResponse("Authentication required.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="TrendFlow Admin"' },
  });
}

export const config = { matcher: ["/admin/:path*", "/admin"] };
