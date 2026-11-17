"""Publishing: review packages as Word, Excel and PowerPoint files, each with a frozen snapshot.

Every figure in a published file is a reference to a stored fact (or to a figure derived from
stored facts by a recorded sum or count). `content` assembles the structure, `excel`, `word` and
`deck` render it, `service` freezes the snapshot and keeps the package records, and `verify`
reopens the files and proves that every figure resolves.
"""
