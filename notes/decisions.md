# 2026-02-18

- Added the new API ticket as `API-3` to continue existing API task numbering in `tasks.json`.
- Added the MCP ticket as `MCP-1` and linked it with `dependsOn: ["API-3"]` so tooling work is explicitly gated on API availability.
- Implemented editor control as a command API (`POST /api/editor/action`) backed by direct editor method calls, not event simulation, to keep behavior deterministic for agent loops.
- Added explicit API state and feature-matrix read endpoints so MCP clients can discover capabilities and verify tool state after each action.
- Scoped this API revision to monster mode and marked background/tile workflows as intentional limitations in the feature matrix to avoid ambiguous partial behavior.
- Implemented MCP transport as a lightweight in-repo JSON-RPC stdio server (no new external dependency), keeping deployment simple for local agent runtimes.
- MCP tool outputs include both text and structured content to support autonomous loop consumption while remaining compatible with generic MCP clients.
- Added dedicated `monster_stamp_pattern` MCP tool to support higher-level sprite stamping while still translating to deterministic API draw actions.
- For Novastar sprite authoring, used a fixed 6-color high-contrast palette and explicit silhouette-first draw phases (erase -> silhouette -> primaries -> details) so 32x32 readability and front/back visual consistency are preserved under MCP-only automation.
