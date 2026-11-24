ESTIMATE, not a measurement. Prices: claude-opus-5-5 at $4.00 input / $20.00 output per million tokens, claude-sonnet-5-5 at $2.00 input / $10.00 output per million tokens (Claude API skill model table, cached 2026-11-03); tokens per call from the three recorded borrowers; the range is 0.6x to 1.6x.

Scope: 17 borrowers (the 16 innovation clients and Pellham Grain); lumora-health makes no model call in the stand-in cycle.

## Calls and cost by agent, claude-opus-5-5 (ESTIMATE)

| agent | calls (ESTIMATE) | mid (ESTIMATE) |
|---|---:|---:|
| certificate | 15 | $0.50 |
| collateral | 1 | $0.09 |
| covenant | 15 | $0.23 |
| early_warning | 14 | $0.31 |
| intake | 16 | $0.41 |
| review | 25 | $1.63 |
| spreading | 46 | $8.77 |

## Totals (ESTIMATE)

| model | low (ESTIMATE) | mid (ESTIMATE) | high (ESTIMATE) |
|---|---:|---:|---:|
| claude-opus-5-5 | $7.16 | $11.93 | $19.09 |
| claude-sonnet-5-5 | $3.58 | $5.97 | $9.55 |

## Extra if the kept three borrowers are re-recorded (ESTIMATE, a separate line)

| model | low (ESTIMATE) | mid (ESTIMATE) | high (ESTIMATE) |
|---|---:|---:|---:|
| claude-opus-5-5 | $0.43 | $0.71 | $1.14 |
| claude-sonnet-5-5 | $0.21 | $0.36 | $0.57 |

| agent | calls (ESTIMATE) | mid, claude-opus-5-5 (ESTIMATE) |
|---|---:|---:|
| intake | 3 | $0.08 |
| review | 1 | $0.07 |
| spreading | 3 | $0.57 |

Everything together on claude-opus-5-5 (ESTIMATE): mid $12.65, high $20.23.

## Tokens per call used (mean of the recordings)

| agent | input | cache write | cache read | output |
|---|---:|---:|---:|---:|
| certificate | 4 | 5326 | 0 | 319 |
| collateral | 4 | 8174 | 0 | 2626 |
| covenant | 2 | 2211 | 5836 | 161 |
| early_warning | 4 | 1916 | 0 | 614 |
| intake | 4 | 4170 | 0 | 232 |
| review | 4 | 4487 | 2414 | 2114 |
| spreading | 4 | 12324 | 0 | 6447 |

## How these numbers were made, and what they leave out

- covenant: 3 exception work items in the stand-in cycles x 5 recorded exchanges per investigation = 15 calls (counted from the call site, the stand-in does not answer it).
- early_warning: one call for each of the 14 borrowers whose cycle fires a signal (call site).
- review: 15 stand-in answers x 1.67 exchanges per recorded cycle = 25 calls.
- The kept three borrowers are re-recorded only if the owner does not accept the stale replay (--accept-stale); the separate line is their stale intake and spreading calls plus briarstone's missing review/02.
- Spreading is priced at the mean of three recorded statement spreads (about 12k cached input, 6.4k output); the stand-in's spreads of monthly packs, MRR and bank statements are likely shorter, so the spreading line leans high; the 0.6x to 1.6x range is a judgement, not a statistic.
- Tokens are taken as the same for the cheaper model (same tokenizer family per the skill); Sonnet's quality on these readings is unmeasured here, so its figure is a price comparison, not a recommendation. No configuration was changed.
- Not counted: the Terms Agent (not called in these cycles), re-runs after a product fix, the one-borrower trial, and any retry the real model causes beyond the recorded exchange counts.
