import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

interface Manifest {
  manifest_version: string;
  name: string;
  display_name: string;
  version: string;
  icon: string;
  icons: Array<{ src: string; size: string }>;
  server: {
    type: string;
    entry_point: string;
    mcp_config: {
      command: string;
      args: string[];
      env: Record<string, string>;
    };
  };
  tools: Array<{ name: string; description: string }>;
  tools_generated: boolean;
  privacy_policies: string[];
  compatibility: {
    platforms: string[];
    runtimes: {
      node: string;
    };
  };
  user_config: Record<
    string,
    {
      type: string;
      title: string;
      description: string;
      sensitive?: boolean;
      required?: boolean;
      default?: string;
    }
  >;
}

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(readFileSync(join(packageRoot, "manifest.json"), "utf8")) as Manifest;
const packageJson = JSON.parse(readFileSync(join(packageRoot, "package.json"), "utf8")) as { version: string };
const readme = readFileSync(join(packageRoot, "README.md"), "utf8");
const submissionNotes = readFileSync(join(packageRoot, "SUBMISSION.md"), "utf8");

describe("MCPB manifest", () => {
  it("declares public-safe A2CR extension metadata", () => {
    expect(manifest.manifest_version).toBe("0.3");
    expect(manifest.name).toBe("a2cr");
    expect(manifest.display_name).toBe("A2CR");
    expect(manifest.version).toBe(packageJson.version);
    expect(manifest.privacy_policies).toEqual(["https://github.com/a2cr/a2cr/blob/main/docs/privacy.md"]);
  });

  it("runs the bundled Node entrypoint through portable MCP config", () => {
    expect(manifest.server).toMatchObject({
      type: "node",
      entry_point: "dist/index.js",
      mcp_config: {
        command: "node",
        args: ["${__dirname}/dist/index.js"],
        env: {
          A2CR_CLIENT_TYPE: "claude",
        },
      },
    });
    expect(manifest.compatibility).toEqual({
      platforms: ["darwin", "win32"],
      runtimes: { node: ">=22.0.0" },
    });
  });

  it("collects only the required user-facing configuration", () => {
    expect(manifest.user_config).toEqual({});
  });

  it("lists the current submitted tool surface", () => {
    expect(manifest.tools.map((tool) => tool.name).sort()).toEqual([
      "delete_work_stash",
      "get_account_limits",
      "get_work_stash",
      "list_contexts",
      "list_work_stash",
      "load_context",
      "save_context",
      "store_work_stash",
    ]);
    expect(manifest.tools.every((tool) => tool.description.length > 20)).toBe(true);
    expect(manifest.tools_generated).toBe(false);
  });

  it("keeps the packaged README ready for local connector privacy review", () => {
    expect(readme).toContain("## Privacy Policy");
    expect(readme).toContain("https://github.com/a2cr/a2cr/blob/main/docs/privacy.md");
    expect(readme).toContain("Data collection");
    expect(readme).toContain("Usage and storage");
    expect(readme).toContain("Third-party sharing");
    expect(readme).toContain("Data retention");
    expect(readme).toContain("Contact");
    expect(readme).toContain("## Reviewer Setup");
    expect(readme).toContain("does not require an A2CR account");
    expect(readme).toContain("repository.");
  });

  it("keeps public-safe Claude directory submission notes", () => {
    expect(submissionNotes).toContain("Connector type: Desktop extension / MCPB.");
    expect(submissionNotes).toContain("Tool annotations");
    expect(submissionNotes).toContain("readOnlyHint: false");
    expect(submissionNotes).toContain("destructiveHint: true");
    expect(submissionNotes).toContain("openWorldHint: false");
    expect(submissionNotes).toContain("Test credentials");
    expect(submissionNotes).toContain("Not required");
    expect(submissionNotes).toContain("Allowed link URIs");
    expect(submissionNotes).toContain("Not used");
    expect(submissionNotes).toContain("Working examples");
    expect(submissionNotes).toContain("MCP Inspector");
    expect(submissionNotes).toContain("contains no reviewer credentials");
  });

  it("references a square PNG icon inside the package", () => {
    expect(manifest.icon).toBe("assets/icon.png");
    expect(manifest.icons).toEqual([{ src: "assets/icon.png", size: "512x512" }]);

    const icon = readFileSync(join(packageRoot, manifest.icon));
    expect(icon.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
    expect(icon.readUInt32BE(16)).toBe(512);
    expect(icon.readUInt32BE(20)).toBe(512);
  });
});
