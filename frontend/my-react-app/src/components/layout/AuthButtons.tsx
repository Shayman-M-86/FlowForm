import { useAuth0 } from "@auth0/auth0-react";

export function AuthButtons() {
    const {
        isAuthenticated,
        user,
        loginWithRedirect,
        logout,
    } = useAuth0();

    const signup = () =>
        loginWithRedirect({
            authorizationParams: {
                screen_hint: "signup",
            },
        });

    const login = () => loginWithRedirect();

    const handleLogout = () =>
        logout({
            logoutParams: {
                returnTo: window.location.origin,
            },
        });

    if (isAuthenticated) {
        return (
            <div>
                <span>{user?.email}</span>
                <button onClick={handleLogout}>Logout</button>
            </div>
        );
    }

    return (
        <div>
            <button onClick={signup}>Signup</button>
            <button onClick={login}>Login</button>
        </div>
    );
}