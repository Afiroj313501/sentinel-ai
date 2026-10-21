import { describe, expect, it } from "vitest";
import { REPO_URL_ERROR, validateRepoUrl } from "./github";

describe("validateRepoUrl", () => {
  it.each([
    "https://github.com/octocat/Hello-World",
    "  https://github.com/octocat/Hello-World.git  ",
    "https://github.com/octocat/Hello-World/",
    "HTTPS://GitHub.com/octocat/Hello-World?tab=readme#top",
    "https://github.com/octocat/Hello-World/tree/main",
    "https://github.com/octocat/Hello-World/tree/feature/login/",
  ])("accepts %j", (value) => {
    expect(validateRepoUrl(value)).toBeNull();
  });

  it.each([
    "",
    "   ",
    "octocat/Hello-World",
    "git@github.com:octocat/Hello-World.git",
    "http://github.com/octocat/Hello-World",
    "ftp://github.com/octocat/Hello-World",
    "https://evil.example/octocat/Hello-World",
    "https://github.com.evil.example/octocat/Hello-World",
    "******github.com/octocat/Hello-World",
    "https://github.com:8443/octocat/Hello-World",
    "https://localhost/octocat/Hello-World",
    "https://169.254.169.254/octocat/Hello-World",
    "https://github.com/octocat",
    "https://github.com/octocat/Hello-World/issues",
    "https://github.com/octocat/Hello-World/tree",
    "https://github.com/octocat/Hello-World/tree/../secret",
    "https://github.com/-bad/Hello-World",
    "https://github.com/octocat/..",
    "https://github.com/octocat/Hello%2eWorld",
    "https://github.com/octocat/Hello-World\nHost: evil.example",
    "https://github.com/octocat/Hello-World\\..\\x",
    `https://github.com/${"a".repeat(300)}`,
  ])("rejects %j", (value) => {
    expect(validateRepoUrl(value)).toBe(REPO_URL_ERROR);
  });

  it("explains what a valid URL looks like", () => {
    expect(REPO_URL_ERROR).toContain("public GitHub repository URL");
    expect(REPO_URL_ERROR).toContain("https://github.com/owner/repo");
  });
});
