import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Lock, LogIn, Mail } from "lucide-react";
import { useAuth } from "../context/useAuth";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <div style={{ width: "100%", maxWidth: 400 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            className="brand-mark"
            style={{ width: 44, height: 44, margin: "0 auto 12px auto" }}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M12 2.8 20 6v5.8c0 4.7-3.4 7.7-8 9.5-4.6-1.8-8-4.8-8-9.5V6l8-3.2Z" />
              <path d="m8.3 12 2.4 2.4 5-5.2" />
            </svg>
          </div>
          <div className="brand-name" style={{ fontSize: 22 }}>
            sentinel<span style={{ color: "var(--blue)" }}>.ai</span>
          </div>
          <p className="muted small" style={{ marginTop: 4 }}>
            Sign in to access your security workspace
          </p>
        </div>

        <article className="card" style={{ padding: 24 }}>
          {error && (
            <p role="alert" className="alert alert-error" style={{ marginBottom: 16 }}>
              {error}
            </p>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label className="label" htmlFor="login-email">
                Email Address
              </label>
              <div className="input-wrap">
                <Mail aria-hidden="true" size={16} />
                <input
                  id="login-email"
                  type="email"
                  required
                  autoFocus
                  className="input"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="login-password">
                Password
              </label>
              <div className="input-wrap">
                <Lock aria-hidden="true" size={16} />
                <input
                  id="login-password"
                  type="password"
                  required
                  className="input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
              style={{ width: "100%", justifyContent: "center", marginTop: 8 }}
            >
              <LogIn size={16} aria-hidden="true" />
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="small muted" style={{ textAlign: "center", marginTop: 20, marginBottom: 0 }}>
            Don't have an account?{" "}
            <Link to="/register" className="text-btn">
              Create an account →
            </Link>
          </p>
        </article>
      </div>
    </div>
  );
}
