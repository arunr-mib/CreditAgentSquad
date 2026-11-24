# Example review package

One borrower's review package for the period ended 30 September 2026, in Word, Excel and PowerPoint. Synthetic data; the lender is the fictional Bank of Stoic.

**How it was made.** `uv run python -m evals.examples` loads the borrower, runs its monitoring cycle end to end, and renders the package from what the cycle stored. The documents were read by the evaluation's stand-in reader (a perfect reader built from the synthetic book's ground truth), not by a model. No model has produced any figure or sentence in these files.

**What the sources show** (workbook, `Sources` sheet, 793 rows when last built):

| Kind | Rows | What the source column gives |
|---|---|---|
| Read from a document | 37 | Document title, page, and the text as printed beside its row label. These are the current period's statement lines. |
| Loaded history | 595 | "loaded from synthetic ground truth, not extracted". The eight earlier quarters were loaded, not read from documents, so they have no page. |
| Calculated | 154 | The calculation, its version and each input with its fact id |
| System of record | 7 | The connector, record and as-of date |

So a page citation exists only for figures that were actually read from a document. In a live deployment history would also be read or come from a system of record.

**Not verified.** The files were opened with LibreOffice and python libraries only, not Microsoft Office.
