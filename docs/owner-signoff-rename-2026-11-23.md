# Answer-key signatures carried across the client rename, 23 November 2026

The owner signed all 107 rows of the innovation answer key on 21 November (`docs/owner-signoff-2026-11-21.md`). On 22 November the owner had eight invented clients renamed (`docs/product/name-check-2026-11-22.md`). The rename carried the signatures over because **no figure, threshold, outcome, period or scenario changed**; only names, codes and the ids built from codes did.

| Old name (code) | New name (code) | Key rows |
|---|---|---|
| Dataflake Inc (dataflake) | Datamarrow Inc (datamarrow) | 10 |
| Quillon AI (quillon-ai) | Tarnavi AI (tarnavi-ai) | 4 |
| Lumora Health (lumora-health) | Calvere Health (calvere-health) | 5 |
| Halcyon Grid (halcyon-grid) | Tavernel Grid (tavernel-grid) | 6 |
| Tessaract Labs (tessaract-labs) | Vantrell Labs (vantrell-labs) | 4 |
| Corvane Analytics (corvane-analytics) | Meridew Analytics (meridew-analytics) | 8 |
| Tidewell Medical (tidewell-medical) | Brackmere Medical (brackmere-medical) | 7 |
| Stripple Tech (stripple-tech) | Cindrel Tech (cindrel-tech) | 6 |

Fifty of the 107 rows belong to these eight; the other 57 are untouched. The scenario `stripple_package` is now `cindrel_package`.

## How the signatures were carried

- The rule is unchanged: the generator keeps a row's signature only if every value in the row is the same as in a signed row (`synthetic.generate._keep_sign_off`). A changed figure still comes back unsigned.
- The old key's rows were renamed as text (names and codes only), then the book was regenerated (`uv run python -m synthetic.books.innovation.generate`). The generator's self-check passed, and its own rule matched all 107 rows, so all 107 stayed signed. No row was signed by hand and `evals.signoff apply` was not used.
- Figures could not move: a client's random draws (and the credit officer who approved its terms) are chosen from its code, so the eight keep their old code as the seed (`synthetic/books/innovation/renames.py`).

## Proof (before = commit `7e62c2a`, after = this commit's key)

- Rows: 107 before, 107 after. Signed: 107 before, 107 after.
- Columns `period_end`, `kind`, `expected_value`, `threshold`, `expected_outcome`: identical in every row, byte for byte, with no normalising.
- With the old names and codes replaced by the new ones, the whole file is identical, every column including `owner_signed_off`: sha256 of the normalised before file and of the after file are both `2d6c234687af014b0c65fdaeff6c77ebe3af73ff34938a5aaa351ba634e39e3b` (before raw: `a37c716b…f6227c6`).
- The only `item` values that changed are two that name a document by its code (`document:cindrel-tech.mrr-export`, `document:cindrel-tech.mf-2026-10-31`).
- Beyond the key: the twelve clients not renamed have byte-identical truth files and documents; the eight renamed truth files are identical once names are normalised (document hashes aside, because the documents print the new names); their 113 documents carry the same words, and six of them wrap one line differently because a name is longer or shorter. Page counts are unchanged.

Reproduce:

```bash
SED='s/dataflake/datamarrow/g; s/Dataflake/Datamarrow/g; s/quillon/tarnavi/g; s/Quillon/Tarnavi/g; s/lumora/calvere/g; s/Lumora/Calvere/g; s/halcyon/tavernel/g; s/Halcyon/Tavernel/g; s/tessaract/vantrell/g; s/Tessaract/Vantrell/g; s/corvane/meridew/g; s/Corvane/Meridew/g; s/tidewell/brackmere/g; s/Tidewell/Brackmere/g; s/stripple/cindrel/g; s/Stripple/Cindrel/g'
git show 7e62c2a:synthetic/books/innovation/oracle.csv | sed -e "$SED" | diff - synthetic/books/innovation/oracle.csv && echo identical
```

## What the owner may want to know

- Nothing needs signing again. If the owner prefers to re-read the 50 renamed rows, `uv run python -m evals.signoff table` lists unsigned rows only, so it shows none; read them in `synthetic/books/innovation/oracle.csv`.
- The recorded model answers for the eight are archived, not replayed (`evals/recordings-archive/renamed-2026-11-22/`). Re-recording them is billable and waits for the owner's go-ahead.
