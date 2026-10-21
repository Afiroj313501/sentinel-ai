import { describe, expect, it } from "vitest";
import { parseSnippet } from "./snippet";

describe("parseSnippet", () => {
  it("splits numbered lines into number and code", () => {
    expect(parseSnippet("1 | import os\n2 | eval(x)")).toEqual([
      { number: 1, code: "import os" },
      { number: 2, code: "eval(x)" },
    ]);
  });

  it("handles padded line numbers and keeps the code's own indentation", () => {
    expect(parseSnippet(" 9 |     return 1\n10 | ")).toEqual([
      { number: 9, code: "    return 1" },
      { number: 10, code: "" },
    ]);
  });

  it("accepts an empty line with no trailing space after the pipe", () => {
    expect(parseSnippet("10 |")).toEqual([{ number: 10, code: "" }]);
  });

  it("keeps lines that do not match as plain text without a number", () => {
    expect(parseSnippet("garbage line")).toEqual([{ number: null, code: "garbage line" }]);
  });

  it("does not treat pipes inside the code as separators", () => {
    expect(parseSnippet("3 | a | b")).toEqual([{ number: 3, code: "a | b" }]);
  });
});
