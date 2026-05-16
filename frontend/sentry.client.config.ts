import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,

  // Low sample rate in prod; off in dev/test
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 0,

  // No session replay — avoids capturing PII from user interactions
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,

  // Only initialise when a DSN is provided
  enabled: !!process.env.NEXT_PUBLIC_SENTRY_DSN,
});
