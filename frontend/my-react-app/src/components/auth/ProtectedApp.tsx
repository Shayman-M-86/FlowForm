import { useEffect, useState, type ReactNode } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { ApiRequestError } from "../../api/client";
import { useApi } from "../../api/useApi";
import { getAuthReturnTo } from "../../auth/redirect";
import "./ProtectedApp.css";

type ProtectedAppProps = {
    children: ReactNode;
};

export function ProtectedApp({ children }: ProtectedAppProps) {
    const { isLoading, isAuthenticated, getIdTokenClaims, loginWithRedirect, logout, error, user } = useAuth0();
    const { bootstrapCurrentUser } = useApi();
    const [bootstrapReady, setBootstrapReady] = useState(false);
    const [bootstrapError, setBootstrapError] = useState<string | null>(null);
    const [bootstrapErrorCode, setBootstrapErrorCode] = useState<string | null>(null);
    const [bootstrapAttempt, setBootstrapAttempt] = useState(0);

    useEffect(() => {
        if (isLoading || !isAuthenticated) {
            setBootstrapReady(false);
            setBootstrapError(null);
            setBootstrapErrorCode(null);
            return;
        }

        const userSub = user?.sub;
        if (!userSub) {
            setBootstrapReady(false);
            setBootstrapError(null);
            setBootstrapErrorCode(null);
            return;
        }

        const markerKey = `flowform:user-bootstrapped:${userSub}`;
        if (window.localStorage.getItem(markerKey) === "true") {
            setBootstrapReady(true);
            setBootstrapError(null);
            setBootstrapErrorCode(null);
            return;
        }

        let cancelled = false;

        setBootstrapReady(false);
        setBootstrapError(null);
        setBootstrapErrorCode(null);

        void (async () => {
            try {
                const claims = await getIdTokenClaims();
                const idToken = claims?.__raw;

                if (!idToken) {
                    throw new Error("Auth0 did not return a raw ID token.");
                }

                await bootstrapCurrentUser(idToken);
                window.localStorage.setItem(markerKey, "true");

                if (!cancelled) {
                    setBootstrapReady(true);
                }
            } catch (err) {
                if (!cancelled) {
                    setBootstrapReady(false);
                    setBootstrapErrorCode(
                        err instanceof ApiRequestError ? err.error.code : null,
                    );
                    setBootstrapError(
                        err instanceof Error ? err.message : "Failed to finish account setup.",
                    );
                }
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [bootstrapAttempt, bootstrapCurrentUser, getIdTokenClaims, isAuthenticated, isLoading, user?.sub]);

    const bootstrapNeedsLogin = bootstrapErrorCode === "AUTH0_CLIENT_ID_NOT_CONFIGURED";

    if (isLoading) {
        return (
            <div className="auth-gate">
                <div className="auth-card">
                    <h1>Checking session</h1>
                    <p>Loading your workspace...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="auth-gate">
                <div className="auth-card">
                    <h1>Authentication error</h1>
                    <p>{error.message}</p>
                    <button
                        onClick={() =>
                            loginWithRedirect({
                                appState: { returnTo: getAuthReturnTo() },
                            })
                        }
                    >
                        Try again
                    </button>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="auth-gate">
                <div className="auth-card">
                    <p className="auth-eyebrow">FlowForm</p>
                    <h1>Sign in to continue</h1>
                    <p>
                        You need to log in to access your projects, surveys, and submissions.
                    </p>

                    <div className="auth-actions">
                        <button
                            onClick={() =>
                                loginWithRedirect({
                                    appState: { returnTo: getAuthReturnTo() },
                                })
                            }
                        >
                            Log in
                        </button>
                        <button
                            className="secondary"
                            onClick={() =>
                                loginWithRedirect({
                                    appState: { returnTo: getAuthReturnTo() },
                                    authorizationParams: { screen_hint: "signup" },
                                })
                            }
                        >
                            Create account
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!bootstrapReady) {
        return (
            <div className="auth-gate">
                <div className="auth-card">
                    <h1>
                        {bootstrapNeedsLogin
                            ? "Sign in to continue"
                            : bootstrapError
                              ? "Account setup failed"
                              : "Setting up your account"}
                    </h1>
                    <p>
                        {bootstrapNeedsLogin
                            ? "FlowForm could not finish account setup because Auth0 is not fully configured on the backend. Sign in again after the configuration is restored."
                            : bootstrapError ?? "Finishing your FlowForm account before opening the workspace."}
                    </p>
                    {bootstrapNeedsLogin ? (
                        <div className="auth-actions">
                            <button
                                onClick={() =>
                                    loginWithRedirect({
                                        appState: { returnTo: getAuthReturnTo() },
                                    })
                                }
                            >
                                Log in
                            </button>
                            <button
                                className="secondary"
                                onClick={() =>
                                    logout({
                                        logoutParams: { returnTo: window.location.origin },
                                    })
                                }
                            >
                                Log out
                            </button>
                        </div>
                    ) : (
                        bootstrapError && (
                            <button onClick={() => setBootstrapAttempt((current) => current + 1)}>
                                Retry
                            </button>
                        )
                    )}
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
