"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { useCreateWatchedIndex } from "@/lib/hooks/useWatchlist";
import {
  WatchedIndexCreateSchema,
  type WatchedIndexCreate,
} from "@/lib/schemas/watchlist";
import { Plus } from "lucide-react";

export function AddWatchedIndexDialog() {
  const [open, setOpen] = useState(false);
  const { mutateAsync, isPending } = useCreateWatchedIndex();
  const form = useForm<WatchedIndexCreate>({
    resolver: zodResolver(WatchedIndexCreateSchema),
    defaultValues: { index_number: "" as unknown as number, label: "", semester_code: "92026" },
  });

  async function onSubmit(values: WatchedIndexCreate) {
    try {
      await mutateAsync(values);
      toast.success(`Index ${values.index_number} added to watchlist`);
      form.reset();
      setOpen(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to add index";
      if (msg.includes("409") || msg.includes("already")) {
        toast.error("This index is already in your watchlist");
      } else {
        toast.error(msg);
      }
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
        Add Index
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-mono">Add Course Index</DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
              <FormField
                control={form.control}
                name="index_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                      Index Number
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="e.g. 01234"
                        className="bg-input border-border font-mono text-sm"
                        {...field}
                        onChange={(e) =>
                          field.onChange(
                            e.target.value === "" ? "" : Number(e.target.value)
                          )
                        }
                      />
                    </FormControl>
                    <FormDescription>
                      5-digit Rutgers section index (1–99999)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="label"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                      Custom Label{" "}
                      <span className="text-muted-foreground normal-case">(optional)</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Overrides the auto-filled course name"
                        className="bg-input border-border font-mono text-sm"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Leave blank to use the course name from the SOC
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="semester_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                      Semester Code
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="92026"
                        className="bg-input border-border font-mono text-sm"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      5-digit code — 92026 = Fall 2026
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setOpen(false)}
                  disabled={isPending}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isPending}
                  className="font-mono uppercase tracking-widest text-xs"
                >
                  {isPending ? (
                    <span className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                      Adding...
                    </span>
                  ) : (
                    "Add"
                  )}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
