# master2 interface review and local integration

## Reviewed source

- GitHub source: `origin/master2`, commit `6123ef2`.
- Original working backend: `bca42be` on `codex/v2-refactor`.
- Local integration branch: `codex/master2-integration`.

The remote branch was inspected in a detached worktree under `.worktrees/master2-review`. Its contents and the remote branch are unchanged. The original branch remains available.

## Important finding

`master2` is more than a design change. It removes the Python package, FastAPI routes, LangGraph workflow, Streamlit entry points, Python dependency manifest and backend tests. It adds an Express `server.ts` with another session/tool implementation. That server does not call Groq or run the original LangGraph agent; its chat behavior uses keyword-based routing.

For this project, the new React presentation was therefore integrated into the existing `frontend/` application while retaining Python, FastAPI, Groq, the original tools, validation, reports, tests and Vite API proxy. The added Express server and its dependencies were not installed into the working application. The frontend API client and shared types remain compatible with the original backend.

## Integration fixes

- Imported the master2 layout, light/dark styles, asset logos, structured replies, sidebar history and illustration assets.
- Removed fixed-point sparklines and synthesized price curves. The source supplies snapshots, not historical observations. Replies show exact prices, reported low/high values, unknown metadata and source evidence instead.
- Read quote currency and period from the original `field_context` contract and mark rounded percentage displays approximate.
- Labelled local news illustrations as decorative, not publisher-supplied photographs; enabled lazy image decoding/loading.
- Fixed the news refresh action to reuse the displayed topic instead of an unrelated search-field value.
- Preserved both Demo/Live session isolation and existing FastAPI checkpoint synchronization, chat, comparisons, news, asset browsing and Markdown exports.

## Verification

Verification passed: 66 Python tests, 23 React tests, the TypeScript/Vite production build, and the local HTTP smoke test for Demo memory, comparisons, exports and CORS. Bounded Live checks returned a BTC snapshot, three Ethereum articles and a correct Ethereum follow-up, all with HTTP 200 and no failed tool results. Regression cases also cover structured reply metadata and absence of invented historical curves.

The embedded browser timed out during preview initialization. Screenshot-based desktop/mobile inspection is therefore still pending; a passing build or simulated DOM interaction test does not establish visual correctness. The illustration images add approximately 2.1 MB in total and are a candidate for later image optimization.

## Run locally

From the repository root:

```powershell
uv run uvicorn crypto_agent.api:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Do not use the remote branch's root-level `npm run dev` instructions for this integrated checkout.
