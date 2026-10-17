import { Link } from "react-router-dom";

export default function NotFound() {
  return <div><h1 className="text-2xl font-semibold">Page not found</h1><p className="mt-2 text-sm text-gray-600"><Link to="/" className="font-medium text-indigo-700 underline">Back to scan history</Link></p></div>;
}
