# Interface design and verification

## Audit

The original interface used a tall hero, large snapshot cards and a split workflow across top-level tabs. Raw tool evidence was separate from the reply it supported. Only a dark palette existed. Conversations could not be restored from a session list, and a long report could overwhelm the research screen.

## Design system

The supplied reference images informed the sidebar, compact market summary and conversation-led workspace. Their charts, sentiment labels, price assumptions and historical metrics are not reproduced: the existing backend does not provide that evidence.

The redesigned Research Desk gives the analyst most of the available width. A secondary panel switches between News and Comparison. Detailed source responses, periods and provenance use expanders. Sidebar destinations reveal focused News, Comparison, Conversations and Reports views.

| Token | Light | Dark |
| --- | --- | --- |
| Page | `#F4F6F7` | `#0C1316` |
| Surface | `#FFFFFF` | `#121B1F` |
| Primary text | `#0F1B20` | `#E7EEF0` |
| Secondary text | `#566870` | `#8FA3AB` |
| Accent | `#09766F` | `#38CDBD` |
| Border | `#DEE4E7` | `#223037` |

The supplied Claude design is integrated in `crypto_agent/ui/design.py`, injected after the base `theme.py` styles. CSS aliases map existing component tokens onto the imported palette. The sidebar and header are more compact, the analyst uses a 520 px conversation area, and the supporting panel has News/Compare/Sources tabs. Native Material icons are excluded from the typography override. The imported design optionally loads Hanken Grotesk from Google Fonts, with system-font fallbacks. No fabricated sparklines or JavaScript framework are added.

## Accessibility and responsiveness

- Native controls have accessible labels; navigation and actions retain keyboard behavior.
- Theme, mode and missing metadata use text, not color alone. Reported changes retain their signs.
- Design-token text/background pairs are tested for at least 4.5:1 contrast; this is not a complete WCAG certification.
- Focus-visible outlines and reduced-motion overrides are included.
- Source links allow HTTP(S) destinations only; untrusted source text is escaped before custom HTML rendering.
- The main columns stack below 760 px; snapshot cards remain compact. Large tables are progressively disclosed.
- Prices retain source precision, and unknown quote currency, periods and timezones are not inferred.

Theme CSS is scoped to Streamlit component/test-ID and keyed-container selectors, not generated Emotion class names. The switch changes only this browser's presentation, not the global server configuration. Streamlit's native Settings appearance and built-in developer chrome remain separate. See the official [theme configuration documentation](https://docs.streamlit.io/develop/api-reference/configuration/config.toml) and [session context documentation](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.context).

## Preserved execution and state

The LangGraph builder, Groq model, API tools, validation and deterministic report renderer are unchanged. A small UI adapter invokes the existing graph on a worker thread and queues safe tool lifecycle labels back to the Streamlit thread. Credentials, tool arguments and model reasoning are not displayed in live progress labels.

Theme and navigation changes preserve the active checkpoint. Asset and news-topic selections survive hidden-view widget cleanup. Conversation archives are held in browser-session memory, preserve the matching live graph, and are isolated by Demo/Live mode. Sources are stored with each AI response so later requests cannot relabel earlier evidence.

## Verification and remaining limits

Offline tests cover existing provider/report regressions plus both themes' contrast tokens, theme/nav state, comparison selection persistence, conversation restoration, Demo/Live isolation, response-specific sources, exports and safe error recovery. Live calls are mocked in UI tests.

Browser QA was attempted, but the embedded browser timed out. Automatic approval rejected reading an unrelated browser page; a dedicated preview tab was created instead. The user then stopped Computer Use with Escape. Therefore final visual checks at desktop/mobile widths and in both themes remain unverified. The legacy screenshot is not evidence of the redesigned UI. No new live-provider smoke test was performed for this frontend change.
