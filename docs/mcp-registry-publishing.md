# MCP Registry Publishing

This note prepares A2CR for publication to the official MCP Registry at the
same time as the public repository and PyPI release.

The official MCP Registry is currently in preview. Registry metadata is
published with `mcp-publisher`, and the registry points to public package
artifacts rather than hosting the package itself.

## Target Entry

| Field | Value |
|---|---|
| Registry server name | `io.github.a2cr/a2cr-mcp` |
| Public repository | `https://github.com/a2cr/a2cr` |
| Package registry | PyPI |
| PyPI package | `a2cr-mcp` |
| Current planned version | `0.1.5` |
| Transport | `stdio` |
| Manifest | `server.json` |

## Required Order

1. Publish the public repository to `a2cr/a2cr`.
2. Publish `a2cr-mcp==0.1.5` to PyPI.
3. Confirm the PyPI README contains:

   ```html
   <!-- mcp-name: io.github.a2cr/a2cr-mcp -->
   ```

4. Run an MCP Registry dry run.
5. Publish to the official MCP Registry.
6. Verify the registry search result.

The PyPI package must exist before the MCP Registry publish step, because the
registry verifies PyPI package ownership by reading the package README and
checking that the `mcp-name` value matches `server.json`.

## Local Manual Flow

Install `mcp-publisher` using the official registry documentation, then run:

```powershell
mcp-publisher --help
mcp-publisher login github
mcp-publisher publish server.json --dry-run
mcp-publisher publish server.json
```

Use GitHub authentication for the `io.github.a2cr/*` namespace. The GitHub
account or organization context used for authentication must be allowed to
publish for the `a2cr` namespace.

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
4. Set `publish=true` when ready to publish the immutable Registry version.

The workflow uses GitHub OIDC for MCP Registry authentication and requires no
dedicated MCP Registry secret. It does not publish to PyPI; PyPI release remains
a separate step.

## References

- https://modelcontextprotocol.io/registry/quickstart
- https://modelcontextprotocol.io/registry/package-types
- https://modelcontextprotocol.io/registry/authentication
- https://modelcontextprotocol.io/registry/github-actions
- https://modelcontextprotocol.io/registry/versioning
