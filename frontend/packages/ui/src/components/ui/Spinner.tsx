interface SpinnerProps {
  size?: number;
}

export function Spinner({ size = 20 }: SpinnerProps) {
  return (
    <span
      className="ui-spinner"
      style={{ width: size, height: size, animationDuration: "0.7s" }}
      role="status"
      aria-label="Loading"
    />
  );
}
