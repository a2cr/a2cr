# MCP Registry Publishing

This note records A2CR's publication flow for the official MCP Registry and the
repeatable steps for future immutable Registry versions.

The official MCP Registry is currently in preview. Registry metadata is
published with `mcp-publisher`, and the registry points to public package
artifacts rather than hosting the package itself.

## Current Status

A2CR is published in the official MCP Registry as
`io.github.a2cr/a2cr-mcp`. Version `0.1.6` is the latest active Registry
version as of 2026-05-20.

## Target Entry

| Field | Value |
|---|---|
| Registry server name | `io.github.a2cr/a2cr-mcp` |
| Public repository | `https://github.com/a2cr/a2cr` |
| Package registry | PyPI |
| PyPI package | `a2cr-mcp` |
| Current published version | `0.1.6` |
| Transport | `stdio` |
| Manifest | `server.json` |

## Required Order For Future Versions

1. Publish the public repository changes to `a2cr/a2cr`.
2. Publish the matching `a2cr-mcp` version to PyPI.
3. Confirm the PyPI README contains:

   ```html
   <!-- mcp-name: io.github.a2cr/a2cr-mcp -->
   ```

4. Run MCP Registry validation.
5. Publish the new unique version to the official MCP Registry.
6. Verify the registry search result.

The PyPI package must exist before the MCP Registry publish step, because the
registry verifies PyPI package ownership by reading the package README and
checking that the `mcp-name` value matches `server.json`. Registry versions are
immutable, so update `server.json` to a version that has not been published
before running `mcp-publisher publish`.

## Local Manual Flow

Install `mcp-publisher` using the official registry documentation, then run:

```powershell
mcp-publisher --help
mcp-publisher login github
mcp-publisher validate server.json
mcp-publisher publish server.json
```

Use GitHub authentication for the `io.github.a2cr/*` namespace. The GitHub
account or organization context used for authentication must be allowed to
publish for the `a2cr` namespace. Run `publish` only for a new immutable
version.

After publishing, verify:

```powershell
Invoke-RestMethod "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.a2cr/a2cr-mcp"
```

## GitHub Actions Flow

The repository includes `.github/workflows/publish-mcp-registry.yml` as a
manual workflow. It is intentionally guarded so it only runs in
`a2cr/a2cr`, not in the private workbench repository.

Use it after the public repo and PyPI package are live:

1. Open GitHub Actions in `a2cr/a2cr`.
2. Run **Publish to MCP Registry**.
3. Keep `publish=false` for validation only.
4. Set `publish=true` when ready to publish a new immutable Registry version.

The workflow uses GitHub OIDC for MCP Registry authentication and requires no
dedicated MCP Registry secret. It does not publish to PyPI; PyPI release remains
a separate step.

## Relationship To Claude And OpenAI

The MCP Registry entry is the first official distribution target because it
matches the current public artifact: a local stdio wrapper distributed through
PyPI.

Claude and OpenAI directory submissions are tracked separately in
`docs/official-distribution-roadmap.md`. In short:

- Claude should receive a local MCPB/Desktop Extension package first, because
  that preserves local encryption.
- OpenAI public distribution should be designed as an Apps SDK remote MCP app
  only after the remote plaintext/privacy boundary is explicit.
- Remote Claude or OpenAI submissions should not block the first public release.

## References

- https://modelcontextprotocol.io/registry/quickstart
- https://modelcontextprotocol.io/registry/package-types
- https://modelcontextprotocol.io/registry/authentication
- https://modelcontextprotocol.io/registry/github-actions
- https://modelcontextprotocol.io/registry/versioning
