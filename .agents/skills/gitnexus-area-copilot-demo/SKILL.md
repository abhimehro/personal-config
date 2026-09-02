---
name: gitnexus-area-copilot-demo
description: "Skill for the Copilot-demo area of personal-config. 8 symbols across 1 files."
---

# Copilot-demo

8 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `copilot-demo/`
- Understanding how getRequiredEnvVar, handleRealtimeError, main work
- Modifying copilot-demo-related functionality

## Key Files

| File                                | Symbols                                                                                                |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `copilot-demo/weather-assistant.ts` | getRequiredEnvVar, handleRealtimeError, main, resetResponseInactivityTimeout, resolveResponseDone (+3) |

## Key Symbols

| Symbol                           | Type     | File                                | Line |
| -------------------------------- | -------- | ----------------------------------- | ---- |
| `getRequiredEnvVar`              | Function | `copilot-demo/weather-assistant.ts` | 13   |
| `handleRealtimeError`            | Function | `copilot-demo/weather-assistant.ts` | 36   |
| `main`                           | Function | `copilot-demo/weather-assistant.ts` | 51   |
| `resetResponseInactivityTimeout` | Function | `copilot-demo/weather-assistant.ts` | 118  |
| `resolveResponseDone`            | Function | `copilot-demo/weather-assistant.ts` | 113  |
| `startSpinner`                   | Function | `copilot-demo/weather-assistant.ts` | 77   |
| `stopSpinner`                    | Function | `copilot-demo/weather-assistant.ts` | 92   |
| `normalizeEndpoint`              | Function | `copilot-demo/weather-assistant.ts` | 27   |

## How to Explore

1. `context({name: "getRequiredEnvVar"})` — see callers and callees
2. `query({search_query: "copilot-demo"})` — find related execution flows
3. Read key files listed above for implementation details
4. `explain({target: "<file or symbol>"})` — persisted taint findings
   (source→sink data flows), when indexed with `--pdg`
