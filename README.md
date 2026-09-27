# AssetFlow — Inventory Monetisation System 📦🤖

### AI-Powered Inventory Analysis & Monetisation Platform

AssetFlow is a multi-agent AI system designed to help businesses analyse inventory, identify potential risks and opportunities, and generate actionable monetisation strategies.

The system analyses inventory data through multiple specialized AI agents and combines their outputs into a unified decision-making workflow.

It was developed as a hackathon project to explore how multi-agent AI can be applied to practical business and inventory-management problems.

---

## 🚀 What Does AssetFlow Do?

Traditional inventory systems mainly focus on tracking stock.

AssetFlow goes a step further by analysing inventory data and asking:

- Which products are becoming slow-moving?
- What products have potential demand?
- Which inventory carries financial or operational risk?
- What actions can be taken to recover or improve inventory value?
- How can different AI analyses be combined into a practical recommendation?

The system processes inventory data and coordinates multiple specialized AI agents to answer these questions.

---

## 🧠 Multi-Agent Architecture

AssetFlow uses specialized AI agents, with each agent focusing on a different aspect of inventory analysis.

```text
                    Inventory Data
                          │
                          ▼
                  ┌───────────────┐
                  │ Data Ingestion │
                  └───────┬───────┘
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ Demand   │ │ Pricing  │ │   Risk   │
       │  Agent   │ │  Agent   │ │  Agent   │
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            └────────────┼────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │    Action   │
                  │    Agent    │
                  └──────┬──────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Decision         │
                │ Aggregator       │
                └────────┬─────────┘
                         │
                         ▼
              Monetisation Strategy
