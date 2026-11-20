# Questions for the owner (collected while you were away)

Each has the decision taken in the meantime; overrule any and I'll rework.

1. **MMAS reference for spreading templates.** I mapped every line of both templates to the conventional sections of a standard bank spread (the structure tools like Moody's MMAS use), using only public section names. If you have licensed MMAS line codes you want matched exactly, share the list and I'll add a code-level mapping. *Taken: generic section mapping.* **Owner (20 Nov): no licensed MMAS version; keep the generic mapping.**
2. **DSCR for startups.** Added for venture borrowers with the same formula as today. A startup with negative EBITDA shows a negative DSCR (a breach); one with no debt service can't be tested. *Taken: as described.* **Owner: yes.**

## Answered

- Squad experience spec, open questions: product name "Credit Squad" on screen (for now); client file redesigned; Night for analysts, Warm paper for officers. Recorded in the spec, section 15. **Owner: yes.**

## Added while you were away (Phase 1 build)

3. **Slipped funding round: what can the officer decide?** A round that passes its expected close raises a high-priority item offering "reviewed" or "escalate to committee", outside the monthly cycle. *Taken: those two options.* **Owner: question unclear.** Reworded: when a startup's expected funding round passes its date without closing, which responses should the alert offer? Proposed (industry practice), unless the owner says otherwise: (1) ask the client for a new timeline (Squad drafts the email; default), (2) note and keep watching, (3) reserve rights, (4) escalate to the credit officer or committee. **Owner (20 Nov): agreed, these four.**
4. **"Runway falling three months running".** Implemented as three successive monthly declines (four monthly figures). *Taken: as described.* **Owner: yes.**
5. **Monthly vs quarterly packs.** A pack whose heading says one/two/four/five/seven/eight/ten/eleven months, or "month ended", is filed as monthly financials; three/six/nine months stay quarterly interim statements. *Taken: as described; the Intake agent can still disagree and a person resolves it.* **Owner: yes.**
6. **Startup DSCR deductions.** Startups have no tax-paid or distributions lines, so a DSCR covenant that names those deductions on a startup can't be tested (shown as missing data). *Taken: as described.* **Owner: yes.**
7. **A cash-flow-positive startup whose certificate says it's not in compliance.** Runway is "not meaningful", so the bank's result is compliant; the certificate's own runway figure is ignored, but its "not in compliance" flag is still reported as a disagreement. *Taken: as described.* **Owner: agreed.**

## Standing approvals (owner, 20 Nov)

1. Phase plans are pre-approved: each plan is written, the owner is told, and building starts after a 10-minute objection window.
2. Live evaluation run in Phase 3 approved up to about $15 (estimate), once the stand-in gate passes and the answer key is signed.
3. The owner will sign the new answer key; it will come as one short table.
4. Phase 4 (experience) runs in parallel with Phases 2–3 in a separate worktree.
5. The test suite may be parallelised (dev-only `pytest-xdist`).
6. Phase 5 hosting pre-approved: a new Vercel project and a new `squad2` schema in the existing Supabase project, free tiers.
7. The owner will start recruiting 4 analysts and 1 credit officer for the usability sessions.
8. Git tags: approved, then skipped by the owner (the session cannot push tags). The pre-v2 version is commit 2292b38.

## Waiting for you (end of Phase 1, 20 Nov)

1. **Start Phases 2 and 4?** Phase 1 is done and verified. I paused before the two builds to stay within "not much beyond $10 while I'm out": Phase 2 is 10 tasks and Phase 4a is 15, each built and reviewed by separate agents. Say "go" and both start (Phase 4 in its own worktree).
2. **Names to check against real companies** before anything is shown outside the team (no web search done): Stripple, Tessaract, Dataflake, Veridia, Halcyon, Quillon first; the full list of 16 companies and 16 officers is in the Phase 2 plan, Task 10.
3. **Phase 2 choices I made where the spec was silent** (plan header, rulings table; overrule any):
   - Figures for the four extra clients:
     - Corvane: $8.4M cash, $0.60M burn, RML 14.0
     - Nimbusfield: $3.3M cash, $0.40M burn, RML 8.3
     - Tidewell: $4.3M cash after the restricted account, $0.35M burn, RML 12.3
     - Ferrogate: $16.0M cash, burn −$0.25M (cash-flow positive)
   - Due days: financials and certificate 30, MRR report 15, bank statements 7.
   - Every client has a drawn Bank of Stoic venture term loan.
   - Ferrogate gets a DSCR covenant from May 2026, per your earlier "have DSCR as well".
4. **SaaS figures on monthly packs:** today every startup spread needs MRR, ARR and customer count. *Proposed: those come from the monthly MRR report, and a financial pack without them still spreads.* This will be built in Phase 2 unless you say otherwise.
