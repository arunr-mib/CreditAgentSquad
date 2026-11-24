# Credit Agent Squad, explained

A plain-language guide for bankers, credit officers and anyone deciding whether to trust it. Written 18 November 2026. Everything described here runs today on synthetic data for a fictional lender, Bank of Stoic.

## The one-paragraph version

Credit Agent Squad is a team of AI agents that runs the quarterly monitoring of a commercial loan book: it collects the borrowers' reporting, spreads the financial statements, tests every covenant, checks borrowing bases, watches for early warning signs and prepares the portfolio review. People step in only where judgement is needed: a breach, a figure the system could not verify, an approval that needs a second person. The system is built so that no number can be invented: the AI never types a figure, code does every calculation, and every number on every screen opens the document page or the calculation it came from.

## The problem it addresses

A mid-sized commercial bank monitors hundreds of borrowers. Each quarter, for each one, an analyst:

1. chases the borrower for statements, a compliance certificate and (for asset-based lines) a borrowing base certificate;
2. keys the statements into a spreading template;
3. recalculates each covenant and compares it with what the borrower certified;
4. recalculates the borrowing base;
5. writes commentary and prepares the review package.

Most of that is reading and arithmetic. The judgement, the part a credit professional is paid for, is a small share of the hours. And the reading and arithmetic is where errors hide: a prior-year column read as the current one, thousands read as units, an add-back counted above its cap, a certificate that says "in compliance" when the numbers say otherwise.

## What the squad does

| Stage of the cycle | Who does the work | Where a person decides |
|---|---|---|
| Compliance tracking | The Terms Agent reads the credit agreement and proposes covenants, definitions and reporting due dates | A second person approves the terms before they govern any test |
| Package collection | The Intake Agent classifies what arrives, matches it to what is due, drafts a chaser for what is missing | A person sends the chaser |
| Spreading | The Spreading Agent reads the statements into a standard template; code checks that they foot | A person confirms figures the checks could not verify |
| Covenant monitoring | Code calculates every covenant; the Certificate Agent reads what the borrower reported; the Covenant Agent investigates a difference | A credit officer decides what to do about a breach |
| Borrowing base | The Collateral Agent reads the certificate and agings; code recalculates eligibility and availability | A credit officer decides on an over-advance |
| Early warning | Code computes signals (shrinking headroom, late reporting, stretched receivables); the Early Warning Agent explains them | A person acknowledges or acts |
| Portfolio review | The Review Agent drafts commentary for each borrower | A person edits it and a second person approves it |
| Package delivery | Code produces the Word, Excel and PowerPoint package from stored figures | A person releases it |

A ninth agent, the Copilot, answers questions about a borrower or the portfolio. It can read; it cannot change anything.

## Why the numbers can be trusted

Four rules do the work. Each is enforced by code, not by asking the AI to behave.

1. **The AI never types a number.** When an agent writes a sentence, a figure appears as a reference to a stored record ("leverage is {fact 1155982e}"). Code looks the record up and prints the figure. If an agent types a digit that is not such a reference, the text is refused.
2. **Every number is a stored fact with a source.** A fact is one of four kinds: read from a document (with the page and the exact place on it), calculated by code (with the formula and its inputs), taken from a system of record, or entered by a person (with their name and reason). Click any figure and its source opens.
3. **Code checks what the AI read.** When the Spreading Agent says "revenue is 48,250 on page 3", code finds that figure on that page itself, reads the row label and the column heading itself, works out the units itself, and holds the figure if anything does not match. The AI's description of where it found something is never taken on trust.
4. **Code calculates; the AI does not.** Ratios, covenant tests, borrowing base availability and headroom are computed by ordinary, tested code using exact decimal arithmetic. A missing input is an error, never treated as zero.

When a check fails, the figure is **held**: it is not used in any calculation until a person decides. The system prefers to stop and ask over guessing.

## What a person sees

The **command centre** is a queue of exceptions, most severe first. Each row says what was found, how severe it is, and whose authority it falls under. Opening one shows:

- the key figures the question turns on (for a covenant: calculated, threshold, reported, headroom), each opening its source;
- the evidence: the calculation, the certificate page, the agreement clause;
- what an agent recommends, if one was asked, clearly marked as written by an agent;
- the decisions allowed, and a reason box.

If the decision is outside the reader's authority (an analyst looking at a breach), the screen says who may decide and routes it to that person in one press. A decision and its reason are recorded permanently.

## What "auditable" means here

- **The ledger.** Every action (a document received, a figure read, a test run, a decision, a routing, a stage started by a person) is written to a ledger that can only be added to. Each entry carries a hash of the one before it, so a change to history is detectable. On the hosted test deployment the application's own database login cannot edit or delete ledger entries.
- **Four eyes.** Terms and commentary need a second person. The system refuses an approval by the person who prepared the work.
- **Versioned terms.** An amendment creates a new version of the terms. Old versions are kept, and a test always records which version it used.
- **Corrections leave a trail.** A figure is never edited. A correction is a new figure that replaces the old one, with the person and reason; everything calculated from the old figure is retired and recalculated.

## What has been verified, and what has not

Verified, on synthetic data:

- The calculation code agrees with the synthetic book's independently generated answers on 378 covenant tests and 24 borrowing base reviews.
- With a stand-in reader (built from the book's ground truth, not a real model), all 21 borrowers run through the cycle: 2,677 of 2,677 figures read correctly, every covenant outcome right, every seeded problem raised as an exception and no false ones.
- 47 deliberate tampering checks (a wrong column, a swapped label, a typed figure in prose, and so on): 46 refused by the product, 1 recovered because code reads the page itself, none slipped through.
- Three independent reviewers were each asked to break the "no wrong number" promise. They found 10, 7 and 7 holes. Every one is fixed and has a permanent test.

Not yet verified:

- **Accuracy with a real AI model is unmeasured.** One live run has been made (18 November 2026, the Review Agent on one borrower). The agent used a stored-fact reference for every figure, and the run surfaced an over-strict wording rule that has since been corrected. One run is not a measurement; the readers of documents (spreading, certificates, borrowing bases, terms) have not yet run with a real model at all.
- A fourth independent review has not been run, and the first three each found something new.
- Real bank documents. The reading rules were written against synthetic statements and reviewers' test layouts. Real statements will include layouts neither covered; the design holds unfamiliar layouts for a person, which is safe but means more touches at first.
- By default a person confirms every document reading. Removing that step for a borrower should follow measured accuracy on that bank's own documents.

## Words used

| Term | Meaning here |
|---|---|
| Fact | One stored number with its source |
| Held | A figure that failed a check and is not used until a person decides |
| Exception (work item) | One question for a person, with its evidence and allowed decisions |
| Cycle | One borrower's monitoring for one period, moving through the stages above |
| Guardrail | A check written in code that the AI's output must pass |
| Ledger | The append-only record of every action |
| Headroom | How far a covenant is from its threshold, as a percentage |
