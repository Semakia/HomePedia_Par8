// Pulsing placeholder block. Uses the `bg-line` token so it adapts to the
// light/dark theme, and Tailwind's built-in `animate-pulse`. Used by the
// route-level loading.tsx skeletons.
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-line ${className}`} />;
}
