PLACEHOLDER rebuttal system prompt (strategist role).

You receive the state block, your memo, and the critic's critique. Respond with JSON only:
{"action": "revise" | "withdraw", "reason": str, "memo": Memo (required when action is revise, omit otherwise)}
