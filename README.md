# fit-tools

Composable Axiom nodes for decoding Garmin/ANT FIT binary fitness-activity
files into clean, structured JSON. Wraps the MIT-licensed
[python-fitparse](https://github.com/dtcooper/python-fitparse) library
(generated from Garmin's own FIT SDK profile) — no reimplementation of the
FIT binary format.

Built for the [Axiom](https://axiomide.com) marketplace, handle
`christiangeorgelucas`.

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
