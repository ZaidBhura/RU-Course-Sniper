import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              // Sentry ingest endpoint needed for browser error reporting.
              `connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"} https://*.ingest.sentry.io`,
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' https://fonts.gstatic.com",
              "img-src 'self' data:",
              "frame-ancestors 'none'",
            ].join("; "),
          },
        ],
      },
    ];
  },

  async rewrites() {
    const apiInternalUrl =
      process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${apiInternalUrl}/api/:path*`,
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  // Suppress Sentry CLI output during builds unless there's an error.
  silent: true,
  // Don't upload source maps (no Sentry org configured yet — M7 sets this up).
  sourcemaps: {
    disable: true,
  },
  // Disable automatic instrumentation injection since we use instrumentation.ts.
  autoInstrumentServerFunctions: false,
});
