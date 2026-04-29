import type { ApiExecutor, BootstrapUserOut } from "./types";

export function bootstrapCurrentUser(
  executor: ApiExecutor,
  idToken: string,
): Promise<BootstrapUserOut> {
  return executor.post<BootstrapUserOut>("/api/v1/auth/bootstrap-user", {
    id_token: idToken,
  });
}
