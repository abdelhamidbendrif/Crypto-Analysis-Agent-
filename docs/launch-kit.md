# Crypto Research AI launch kit

## LinkedIn draft

I built **Crypto Research AI**, a research workspace for exploring Bitcoin and Ethereum through charts, market snapshots and a conversational agent.

In the demo, I open BTC/USD history, ask for a market snapshot, then ask for news about the same asset. The agent remembers the context and shows the sources behind its response. I can also export the research to Markdown.

I built the frontend with React, TypeScript and Recharts. FastAPI connects it to a LangGraph agent running on Groq. CoinGecko supplies price history, with FreeCryptoAPI and NewsAPI providing market snapshots and headlines. The app includes a clearly labelled Demo mode so the main workflow can be tried without provider credentials.

The detail I enjoyed building most was tracking where each value came from. The chart shows when the provider observed a price and when the app retrieved it. Individual answers retain their own evidence, even as the conversation moves on.

Source and setup on GitHub: https://github.com/abdelhamidbendrif/Crypto-Analysis-Agent-/tree/codex/master2-integration

#LangGraph #FastAPI #React #DataScience

## 40-second recording

| Time | On screen | Voiceover |
| --- | --- | --- |
| 0–7 s | Open Research Desk in Live APIs mode and select Chart → BTC → 24 hours. | “I built a workspace for researching crypto prices and news in one conversation.” |
| 7–15 s | Hover over two chart points. Show the CoinGecko label and latest observation time. | “The chart displays timestamped BTC/USD observations from CoinGecko.” |
| 15–26 s | Click BTC snapshot, then send “Find recent news about the same asset.” | “I can ask for a snapshot, then refer to the same asset without typing Bitcoin again.” |
| 26–35 s | Expand Sources & tools and show a publisher link. | “Each tool-backed turn keeps its own source results.” |
| 35–42 s | Export report, then show the repository README. | “The report downloads as Markdown. The repository includes setup and a Demo mode.” |

Rehearse with Live before recording. If provider latency is high, record the submission and the result as separate takes. If you record in Demo, keep the fictional-data label visible and describe the chart as sample data.
