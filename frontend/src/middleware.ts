import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/auth", "/api/auth"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  const hasSession = request.cookies.has("sniper_rt");

  if (!isPublic && !hasSession) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/auth";
    return NextResponse.redirect(loginUrl);
  }

  if (pathname === "/auth" && hasSession) {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    return NextResponse.redirect(dashboardUrl);
  }

  if (pathname.startsWith("/dashboard/admin")) {
    const accessToken = request.cookies.get("sniper_at")?.value;
    if (!accessToken) {
      const dashUrl = request.nextUrl.clone();
      dashUrl.pathname = "/dashboard";
      return NextResponse.redirect(dashUrl);
    }
    try {
      const payload = JSON.parse(
        Buffer.from(accessToken.split(".")[1], "base64url").toString()
      );
      if (!payload.is_superuser) {
        const dashUrl = request.nextUrl.clone();
        dashUrl.pathname = "/dashboard";
        return NextResponse.redirect(dashUrl);
      }
    } catch {
      const dashUrl = request.nextUrl.clone();
      dashUrl.pathname = "/dashboard";
      return NextResponse.redirect(dashUrl);
    }
  }

  const response = NextResponse.next();

  if (
    request.method !== "GET" &&
    pathname.startsWith("/api/auth") &&
    !pathname.includes("/refresh")
  ) {
    const origin = request.headers.get("origin");
    const host = request.headers.get("host");
    if (origin && host) {
      try {
        const originHostname = new URL(origin).hostname;
        const hostHostname = host.split(":")[0];
        if (originHostname !== hostHostname) {
          return new NextResponse(null, { status: 403 });
        }
      } catch {
        return new NextResponse(null, { status: 403 });
      }
    }
  }

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
