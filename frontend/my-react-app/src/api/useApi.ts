import { useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import * as client from "./client";

export function useApi() {
    const { getAccessTokenSilently } = useAuth0();

    const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
        const token = await getAccessTokenSilently();
        return {
            Authorization: `Bearer ${token}`,
        };
    }, [getAccessTokenSilently]);

    const get = useCallback(
        async <T,>(path: string): Promise<T> => {
            const headers = await getAuthHeaders();
            return client.get<T>(path, headers);
        },
        [getAuthHeaders],
    );

    const post = useCallback(
        async <T,>(path: string, body?: unknown): Promise<T> => {
            const headers = await getAuthHeaders();
            return client.post<T>(path, body, headers);
        },
        [getAuthHeaders],
    );

    const patch = useCallback(
        async <T,>(path: string, body: unknown): Promise<T> => {
            const headers = await getAuthHeaders();
            return client.patch<T>(path, body, headers);
        },
        [getAuthHeaders],
    );

    const del = useCallback(
        async (path: string): Promise<void> => {
            const headers = await getAuthHeaders();
            return client.del(path, headers);
        },
        [getAuthHeaders],
    );

    const getWithQuery = useCallback(
        async <T,>(
            path: string,
            params: Record<string, string | number | boolean | undefined>,
        ): Promise<T> => {
            const headers = await getAuthHeaders();
            return client.getWithQuery<T>(path, params, headers);
        },
        [getAuthHeaders],
    );

    return {
        get,
        post,
        patch,
        del,
        getWithQuery,
    };
}