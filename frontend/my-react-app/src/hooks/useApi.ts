import { useAuth0 } from "@auth0/auth0-react";

export function useApi() {
    const { getAccessTokenSilently } = useAuth0();

    async function getProjects() {
        const token = await getAccessTokenSilently();

        const res = await fetch("http://localhost:5000/api/v1/projects", {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (!res.ok) {
            throw new Error("Request failed");
        }

        return res.json();
    }

    return { getProjects };
}