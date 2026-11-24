When a product rule changes on purpose, change the answer key in the same commit, say so, and have the owner re-sign it; never edit the key to make a test pass.

**What happened (18 November 2026).** After an independent review, one late filing stopped raising two exceptions (a chaser and a separate high signal): the late-reporting warning now attaches to the open chaser. The stand-in evaluation then failed on Eastmere because the synthetic answer key still expected the separate signal item.

**Why it was right to change the key here.** The disagreement was not a calculation that one side got wrong (that is the case CLAUDE.md forbids patching: investigate instead). It was a deliberate change to what counts as one question for a person. The key encodes that rule independently (`synthetic/book.py`), so the rule had to be written there too, in the key's own terms (skip `reporting_late` when a chaser is open), not copied from the product code.

**How to apply.**
- Regenerate the book into a scratch folder and diff it against `synthetic/out` first: only the truth files the rule touches should change (here one file; all 360 documents were identical).
- Commit the key change with the product change and name it in the message.
- Tell the owner: the key is theirs to sign, and a changed row needs signing again.

**Also learned the same day.** A rule enforced only in the browser is not enforced: the server accepted breach decisions with no reason and routing to people without the permission. Every rule a person can be held to belongs in the server, with a test that calls the API directly.
