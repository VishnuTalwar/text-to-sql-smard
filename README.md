# Natural-Language Analytics Agent

## Overview
<!-- 2-4 sentences: what does this do, in plain terms? -->
A tool that lets a user ask a question about a database in plain English and get back an answer, without writing SQL. Example: "Which customers spent the most last quarter?" → the agent generates and runs the SQL, then explains the result.

## Architecture

```
User question (English)
   → Schema retrieval (relevant tables/columns)
   → SQL generation (LLM + schema context)
   → SQL validation / safety check
   → Execution against DB
   → Natural-language answer / chart
```

<!-- Replace with your actual diagram once components are finalized -->

## Tech Stack
| Component        | Choice | Why |
|-------------------|--------|-----|
| Backend           |        |     |
| Database          |        |     |
| LLM / API         |        |     |
| Frontend          |        |     |
| Deployment        |        |     |

## Key Design Decisions
<!-- Short bullets — link to DECISIONS.md for detail -->
- Schema grounding approach: 
- SQL generation strategy: 
- Safety / validation approach: 
- Ambiguity handling: 

See `DECISIONS.md` for full reasoning.

## Status
- [ ] Project scaffold
- [ ] Basic single-table NL → SQL loop working end-to-end
- [ ] Multi-table schema grounding
- [ ] Safety/validation layer
- [ ] Ambiguity / clarifying-question handling
- [ ] Response formatting (text + chart)
- [ ] Polish + demo-ready

## Setup
<!-- Fill in once scaffolding exists -->
```bash
# install deps
# set up .env
# run
```

## Example Usage
<!-- Fill in with a real example once working -->
```
Q: 
A: 
```
