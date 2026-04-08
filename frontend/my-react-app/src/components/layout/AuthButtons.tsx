import { useAuth0 } from "@auth0/auth0-react";
import "./AuthButtons.css";

export function AuthButtons() {
  const { isAuthenticated, user, loginWithRedirect, logout } = useAuth0();

  if (isAuthenticated) {
    return (
      <div className="auth-user">
        <span className="auth-user__email">{user?.email}</span>
        <button
          className="auth-user__logout"
          onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
        >
          Log out
        </button>
      </div>
    );
  }

  return (
    <button className="auth-user__logout" onClick={() => loginWithRedirect()}>
      Log in
    </button>
  );
}
