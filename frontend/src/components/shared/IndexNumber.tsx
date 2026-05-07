import { cn } from "@/lib/utils";
import { padIndex } from "@/lib/utils/formatters";

interface IndexNumberProps {
  value: number;
  href?: string;
  className?: string;
}

export function IndexNumber({ value, href, className }: IndexNumberProps) {
  const display = padIndex(value);
  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "font-mono text-sm tracking-wider text-[#e8eaf0] hover:text-primary transition-colors",
          className
        )}
        aria-label={`Course index ${display}`}
      >
        {display}
      </a>
    );
  }
  return (
    <span
      className={cn("font-mono text-sm tracking-wider", className)}
      aria-label={`Course index ${display}`}
    >
      {display}
    </span>
  );
}
