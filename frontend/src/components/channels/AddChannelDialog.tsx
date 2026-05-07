"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateChannel } from "@/lib/hooks/useChannels";
import { ShieldCheck, Plus } from "lucide-react";

const DiscordFormSchema = z.object({
  webhook_url: z
    .string()
    .url("Must be a valid URL")
    .startsWith("https://discord.com/api/webhooks/", "Must be a Discord webhook URL"),
});

const PushoverFormSchema = z.object({
  token: z.string().min(1, "Token is required"),
  user_key: z.string().min(1, "User key is required"),
});

export function AddChannelDialog() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);
  const [channelType, setChannelType] = useState<"discord" | "pushover">("discord");
  const { mutateAsync, isPending } = useCreateChannel();

  const discordForm = useForm({ resolver: zodResolver(DiscordFormSchema), defaultValues: { webhook_url: "" } });
  const pushoverForm = useForm({ resolver: zodResolver(PushoverFormSchema), defaultValues: { token: "", user_key: "" } });

  function handleClose() {
    setOpen(false);
    setStep(1);
    discordForm.reset();
    pushoverForm.reset();
  }

  async function onSubmitDiscord(values: z.infer<typeof DiscordFormSchema>) {
    try {
      await mutateAsync({ channel_type: "discord", credential: values });
      toast.success("Discord channel added");
      handleClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      toast.error(msg.includes("409") || msg.includes("already") ? "Discord channel already configured" : msg);
    }
  }

  async function onSubmitPushover(values: z.infer<typeof PushoverFormSchema>) {
    try {
      await mutateAsync({ channel_type: "pushover", credential: values });
      toast.success("Pushover channel added");
      handleClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      toast.error(msg.includes("409") || msg.includes("already") ? "Pushover channel already configured" : msg);
    }
  }

  return (
    <>
      <Button
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-2 font-mono uppercase tracking-widest text-xs"
      >
        <Plus className="h-3.5 w-3.5" aria-hidden />
        Add Channel
      </Button>

      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-mono">Add Notification Channel</DialogTitle>
          </DialogHeader>

          {step === 1 ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Choose a notification type:</p>
              <div className="grid grid-cols-2 gap-3">
                {(["discord", "pushover"] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => { setChannelType(type); setStep(2); }}
                    className={`flex flex-col items-center gap-2 rounded-sm border p-4 text-sm font-mono uppercase tracking-widest transition-colors hover:border-primary focus-visible:ring-2 focus-visible:ring-primary ${
                      channelType === type ? "border-primary text-foreground" : "border-border text-muted-foreground"
                    }`}
                  >
                    {type === "discord" ? "💬" : "📳"}
                    {type}
                  </button>
                ))}
              </div>
            </div>
          ) : channelType === "discord" ? (
            <Form {...discordForm}>
              <form onSubmit={discordForm.handleSubmit(onSubmitDiscord)} noValidate className="space-y-4">
                <Alert className="flex items-start gap-2 border-[#00c896]/30 bg-[#00c896]/5 text-xs text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-[#00c896] shrink-0 mt-0.5" aria-hidden />
                  <span>Your webhook URL is encrypted and stored securely. We never display it again after saving.</span>
                </Alert>

                <FormField
                  control={discordForm.control}
                  name="webhook_url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                        Discord Webhook URL
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="url"
                          placeholder="https://discord.com/api/webhooks/..."
                          className="bg-input border-border font-mono text-xs"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <DialogFooter className="gap-2">
                  <Button type="button" variant="outline" onClick={() => setStep(1)} disabled={isPending}>
                    Back
                  </Button>
                  <Button type="submit" disabled={isPending} className="font-mono uppercase tracking-widest text-xs">
                    {isPending ? (
                      <span className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                        Saving...
                      </span>
                    ) : "Save"}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          ) : (
            <Form {...pushoverForm}>
              <form onSubmit={pushoverForm.handleSubmit(onSubmitPushover)} noValidate className="space-y-4">
                <Alert className="flex items-start gap-2 border-[#00c896]/30 bg-[#00c896]/5 text-xs text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-[#00c896] shrink-0 mt-0.5" aria-hidden />
                  <span>Your API credentials are encrypted and stored securely. We never display them again after saving.</span>
                </Alert>

                <FormField
                  control={pushoverForm.control}
                  name="token"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                        App Token
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="Pushover application token"
                          className="bg-input border-border font-mono text-xs"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={pushoverForm.control}
                  name="user_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                        User Key
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="Pushover user key"
                          className="bg-input border-border font-mono text-xs"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <DialogFooter className="gap-2">
                  <Button type="button" variant="outline" onClick={() => setStep(1)} disabled={isPending}>
                    Back
                  </Button>
                  <Button type="submit" disabled={isPending} className="font-mono uppercase tracking-widest text-xs">
                    {isPending ? (
                      <span className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                        Saving...
                      </span>
                    ) : "Save"}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
