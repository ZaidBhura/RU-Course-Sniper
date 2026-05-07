"use client";

import { Button } from "@/components/ui/button";

export type LogFilters = {
  status: string;
  channel: string;
  eventType: string;
};

interface LogsFilterProps {
  filters: LogFilters;
  onChange: (filters: LogFilters) => void;
}

type FilterOption = { value: string; label: string };

const statusOptions: FilterOption[] = [
  { value: "", label: "All statuses" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
  { value: "skipped", label: "Skipped" },
];

const channelOptions: FilterOption[] = [
  { value: "", label: "All channels" },
  { value: "discord", label: "Discord" },
  { value: "pushover", label: "Pushover" },
];

const eventOptions: FilterOption[] = [
  { value: "", label: "All events" },
  { value: "open_notify", label: "Course Opened" },
  { value: "close_reset", label: "Course Closed" },
];

function FilterChips({
  options,
  value,
  onChange,
}: {
  options: FilterOption[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-2.5 py-1 text-xs font-mono rounded-sm border transition-colors ${
            value === opt.value
              ? "border-primary text-foreground bg-primary/10"
              : "border-border text-muted-foreground hover:border-muted-foreground"
          }`}
          aria-pressed={value === opt.value}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function LogsFilter({ filters, onChange }: LogsFilterProps) {
  const isFiltered = filters.status || filters.channel || filters.eventType;

  return (
    <div className="flex flex-wrap items-start gap-3">
      <FilterChips
        options={statusOptions}
        value={filters.status}
        onChange={(v) => onChange({ ...filters, status: v })}
      />
      <FilterChips
        options={channelOptions}
        value={filters.channel}
        onChange={(v) => onChange({ ...filters, channel: v })}
      />
      <FilterChips
        options={eventOptions}
        value={filters.eventType}
        onChange={(v) => onChange({ ...filters, eventType: v })}
      />
      {isFiltered && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange({ status: "", channel: "", eventType: "" })}
          className="text-xs font-mono text-muted-foreground h-7"
        >
          Clear
        </Button>
      )}
    </div>
  );
}
