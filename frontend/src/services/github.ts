export const REPO_URL_ERROR =
  "Enter a public GitHub repository URL, like https://github.com/owner/repo.";

const OWNER = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/;
const REPO = /^[A-Za-z0-9._-]{1,100}$/;
const BRANCH = /^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$/;
const MAX_URL_CHARS = 300;

export function validateRepoUrl(value: string): string | null {
  const text = value.trim();
  if (!text || text.length > MAX_URL_CHARS) return REPO_URL_ERROR;
  for (const char of text) {
    const code = char.charCodeAt(0);
    if (code <= 0x20 || code === 0x7f || char === "\\") return REPO_URL_ERROR;
  }

  let url: URL;
  try {
    url = new URL(text);
  } catch {
    return REPO_URL_ERROR;
  }
  if (
    url.protocol !== "https:" ||
    url.hostname !== "github.com" ||
    url.port ||
    url.username ||
    url.password
  ) {
    return REPO_URL_ERROR;
  }

  const segments = url.pathname.split("/").filter(Boolean);
  if (segments.length < 2) return REPO_URL_ERROR;
  const owner = segments[0];
  const repo = segments[1].endsWith(".git") ? segments[1].slice(0, -4) : segments[1];
  if (!OWNER.test(owner) || !REPO.test(repo) || repo === "." || repo === "..") {
    return REPO_URL_ERROR;
  }

  if (segments.length > 2) {
    if (segments[2] !== "tree" || segments.length < 4) return REPO_URL_ERROR;
    const branch = segments.slice(3).join("/");
    if (!BRANCH.test(branch) || branch.split("/").some((part) => part === "." || part === "..")) {
      return REPO_URL_ERROR;
    }
  }
  return null;
}
