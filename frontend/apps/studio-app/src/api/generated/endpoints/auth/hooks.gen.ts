// This file is auto-generated — do not edit manually

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { BootstrapUserRequest } from "./types.gen";
import { bootstrapUser } from "./requests.gen";

export const authKeys = {
  all: () => ["auth"] as const,
};

export function useBootstrapUser() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: BootstrapUserRequest) => bootstrapUser(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: authKeys.all() });
    },
  });
}
