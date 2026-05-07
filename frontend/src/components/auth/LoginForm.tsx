"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { LoginSchema, type LoginInput } from "@/lib/schemas/auth";
import { login } from "@/lib/api/auth";
import { queryKeys } from "@/lib/utils/queryKeys";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function LoginForm({ onSwitchToRegister }: { onSwitchToRegister: () => void }) {
  const router = useRouter();
  const qc = useQueryClient();
  const form = useForm<LoginInput>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginInput) {
    try {
      await login(values);
      await qc.invalidateQueries({ queryKey: queryKeys.session });
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      toast.error(msg);
    }
  }

  const { isSubmitting } = form.formState;

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                Email
              </FormLabel>
              <FormControl>
                <Input
                  type="email"
                  autoComplete="email"
                  placeholder="user@rutgers.edu"
                  className="bg-input border-border font-mono text-sm"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                Password
              </FormLabel>
              <FormControl>
                <Input
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="bg-input border-border font-mono text-sm"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button
          type="submit"
          className="w-full font-mono uppercase tracking-widest"
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
              Signing in...
            </span>
          ) : (
            "Sign in"
          )}
        </Button>

        <p className="text-center text-xs text-muted-foreground">
          No account?{" "}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-primary hover:underline focus-visible:ring-2 focus-visible:ring-primary"
          >
            Register
          </button>
        </p>
      </form>
    </Form>
  );
}
