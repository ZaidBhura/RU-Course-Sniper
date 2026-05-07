interface LoadingRowProps {
  cols: number;
}

export function LoadingRow({ cols }: LoadingRowProps) {
  return (
    <tr aria-busy="true">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 rounded-sm bg-muted animate-pulse" />
        </td>
      ))}
    </tr>
  );
}
