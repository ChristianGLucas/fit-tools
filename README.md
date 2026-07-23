# fit-tools

Composable Axiom nodes for decoding Garmin/ANT FIT binary fitness-activity
files into clean, structured JSON. Wraps the MIT-licensed
[python-fitparse](https://github.com/dtcooper/python-fitparse) library
(generated from Garmin's own FIT SDK profile) — no reimplementation of the
FIT binary format.

Built for the [Axiom](https://axiomide.com) marketplace, handle
`christiangeorgelucas`.

## Use it from your agent or app

Every node in this package is a **live, auto-scaling API endpoint** on the
[Axiom](https://axiomide.com) marketplace — call it from an AI agent or your own
code, with nothing to self-host.

**📦 See it on the marketplace:**
https://dev.axiomide.com/marketplace/christiangeorgelucas/fit-tools@0.1.0

**Hook it up to an AI agent (MCP).** Add Axiom's hosted MCP server to any MCP
client and every node becomes a typed tool your agent can call — search the
catalog, inspect a schema, and invoke it directly.

```bash
# Claude Code
claude mcp add --transport http axiom https://api.axiomide.com/mcp \
  --header "Authorization: Bearer $AXIOM_API_KEY"
```

Claude Desktop, Cursor, or any config-based client:

```json
{
  "mcpServers": {
    "axiom": {
      "type": "http",
      "url": "https://api.axiomide.com/mcp",
      "headers": { "Authorization": "Bearer YOUR_AXIOM_API_KEY" }
    }
  }
}
```

**Call it from the CLI.**

```bash
axiom invoke christiangeorgelucas/fit-tools/GetFileInfo --input '{ ... }'
```

**Call it over HTTP.**

```bash
curl -X POST https://api.axiomide.com/invocations/v1/nodes/christiangeorgelucas/fit-tools/0.1.0/GetFileInfo \
  -H "Authorization: Bearer $AXIOM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{ ... }'
```

> Input/output schema for each node is on the marketplace page above, or via
> `axiom inspect node christiangeorgelucas/fit-tools/GetFileInfo`.

### Get started free

Install the CLI:

```bash
# macOS / Linux — Homebrew
brew install axiomide/tap/axiom

# macOS / Linux — install script
curl -fsSL https://raw.githubusercontent.com/AxiomIDE/axiom-releases/main/install.sh | sh
```

**Windows:** download the `windows/amd64` `.zip` from the
[releases page](https://github.com/AxiomIDE/axiom-releases/releases), unzip it,
and put `axiom.exe` on your `PATH`.

Then `axiom version` to verify, `axiom login` (GitHub or Google) to authenticate,
and create an API key under **Console → API Keys**. Docs and sign-up at
**[axiomide.com](https://axiomide.com)**.

## Nodes

- **GetFileInfo** — file identity (type, manufacturer, product, serial, created time).
- **ListMessageTypes** — inventory of every FIT message type present and its count.
- **ParseActivity** — general-purpose decode: file info + sessions + laps + device info + records in one call.
- **ExtractRecords** — the per-sample activity time series (position, altitude, heart rate, power, cadence, speed, temperature, distance).
- **ExtractSessions** — whole-activity/session summary metrics.
- **ExtractLaps** — per-lap summary metrics and lap-trigger type.
- **ExtractDeviceInfo** — recording device and paired ANT+/Bluetooth sensors.

This package only decodes the FIT binary format. It composes downstream with
[gpx-tools](https://github.com/ChristianGLucas/gpx-tools) (GPS track XML) and
[time-series-tools](https://github.com/ChristianGLucas/time-series-tools)
(statistical analysis of a decoded record series) — it does not duplicate
either.

## License

MIT — see [LICENSE](LICENSE). Wraps python-fitparse (MIT).
