import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <article className="card">
      <p className="empty">
        Page not found.{" "}
        <Link to="/" className="text-btn">
          Back to overview →
        </Link>
      </p>
    </article>
  );
}
