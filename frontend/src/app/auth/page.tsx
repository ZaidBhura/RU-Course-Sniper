"use client";

import { useState } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { RegisterForm } from "@/components/auth/RegisterForm";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logotype */}
        <div className="mb-10 text-center">
          <div className="inline-block">
            <span className="font-mono text-3xl font-bold tracking-[0.2em] text-primary">
              RU
            </span>
            <span className="font-mono text-3xl font-bold tracking-[0.2em] text-foreground">
              {" "}SNIPER
            </span>
          </div>
          <p className="mt-2 text-xs font-mono text-muted-foreground tracking-widest uppercase">
            Course availability monitor
          </p>
        </div>

        {/* Card */}
        <div className="rounded-sm border border-border bg-card p-6 border-t-2 border-t-primary">
          <div role="tablist" className="flex gap-4 mb-6">
            <button
              role="tab"
              onClick={() => setMode("login")}
              className={`flex-1 text-xs font-mono uppercase tracking-widest py-1.5 transition-colors border-b-2 ${
                mode === "login"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              aria-selected={mode === "login"}
            >
              Sign In
            </button>
            <button
              role="tab"
              onClick={() => setMode("register")}
              className={`flex-1 text-xs font-mono uppercase tracking-widest py-1.5 transition-colors border-b-2 ${
                mode === "register"
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              aria-selected={mode === "register"}
            >
              Register
            </button>
          </div>

          {mode === "login" ? (
            <LoginForm onSwitchToRegister={() => setMode("register")} />
          ) : (
            <RegisterForm onSwitchToLogin={() => setMode("login")} />
          )}
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground font-mono">
          Rutgers University · Spring 2026
        </p>
      </div>
    </main>
  );
}
