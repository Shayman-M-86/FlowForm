import { Badge } from "./Badge";
import { Tooltip } from "./Tooltip";

interface PermissionTagProps {
  label: string;
  tooltip: string;
}

export function PermissionTag({ label, tooltip }: PermissionTagProps) {
  return (
    <Tooltip title={tooltip} size="sm">
      <Badge variant="muted" size="xxs">
        {label}
      </Badge>
    </Tooltip>
  );
}
