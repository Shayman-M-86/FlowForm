interface SpinnerProps {
  size?: number;
}

export function Spinner({ size = 20 }: SpinnerProps) {
  return (
    <span
      className="inline-block shrink-0 animate-spin rounded-full border-2 border-border border-t-accent"
      style={{ width: size, height: size, animationDuration: "0.7s" }}
      role="status"
      aria-label="Loading"
    />
  );
}
