import type { ReactNode } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import "./ProtectedApp.css";

type ProtectedAppProps = {
    children: ReactNode;
};

export function ProtectedApp({ children }: ProtectedAppProps) {
    const { isLoading, isAuthenticated, loginWithRedirect, error } = useAuth0();

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
                    <button onClick={() => loginWithRedirect()}>Try again</button>
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
                        <button onClick={() => loginWithRedirect()}>Log in</button>
                        <button
                            className="secondary"
                            onClick={() =>
                                loginWithRedirect({
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

    return <>{children}</>;
}