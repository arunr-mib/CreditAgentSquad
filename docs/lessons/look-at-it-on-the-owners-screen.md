Check every screen at phone and tablet width before handing over a link; a desktop-only check hid a page 600 pixels wider than a phone.

- **What happened (18 November 2026).** The first hosted link was checked at 1280 and 1440 pixels only. The owner opened it on a small screen and reported "truncation everywhere" and a decision card "cut off". Nothing was truncated in the code: `frontend/src/styles.css` set `min-width: 1024px`, so on a phone everything right of the screen edge was simply out of sight.
- **Why it matters.** In credit the exact wording of a covenant name or an outcome is the decision. A reader who sees half of it cannot tell a layout fault from missing data.
- **Rule.** Before a link goes to the owner, measure `document.documentElement.scrollWidth - clientWidth` at 390, 820, 1024 and 1280 pixels on every route; it must be 0. Look at one phone screenshot of each main screen.
- **Also learned.** Feedback can mix this product with screenshots of an older one (it named a borrower and a user that exist only in the design-page fixtures). Check each point against the live screens before changing anything, and say which points did not apply.
