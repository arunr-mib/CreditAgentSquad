from app.guardrails.labels import mapping_doubt, reads_as, similarity

LINES = {
    "bs.long_term_debt": ["Long-term debt, net of current portion"],
    "bs.other_noncurrent_liabilities": ["Other liabilities"],
    "bs.accounts_payable": ["Accounts payable"],
    "bs.accrued_liabilities": ["Accrued liabilities"],
    "bs.revolver": ["Line of credit"],
}


def test_a_label_that_reads_as_another_line_raises_a_doubt():
    doubt = mapping_doubt("Long-term debt, net of current portion", "bs.other_noncurrent_liabilities", LINES)
    assert doubt and "bs.long_term_debt" in doubt
    assert mapping_doubt("Accounts payable", "bs.accrued_liabilities", LINES)
    assert mapping_doubt("Line of credit", "bs.accounts_payable", LINES)


def test_the_right_line_raises_nothing():
    assert mapping_doubt("Long-term debt, net of current portion", "bs.long_term_debt", LINES) is None
    assert mapping_doubt("Accounts payable", "bs.accounts_payable", LINES) is None
    # the same name under two keys (net income on two statements) is not a doubt
    both = {"cf.net_income": ["Net income"], "stated.is.net_income": ["Net income"]}
    assert mapping_doubt("Net income", "cf.net_income", both) is None


def test_an_unfamiliar_label_is_held_until_a_person_has_confirmed_it():
    # a borrower's own wording is not accepted on the reader's say-so
    assert "not a known name" in mapping_doubt("Notes payable to bank", "bs.revolver", LINES)
    assert "not a known name" in mapping_doubt("Trade creditors", "bs.accounts_payable", LINES)
    # a fragment of the right label is not the label
    assert mapping_doubt("net of current portion", "bs.long_term_debt", LINES)
    assert mapping_doubt("liabilities", "bs.other_noncurrent_liabilities", LINES)
    assert "no row label" in mapping_doubt("  ", "bs.revolver", LINES)
    # once a person has confirmed the label for the line, it is known for that borrower
    assert mapping_doubt("Notes payable to bank", "bs.revolver", LINES, confirmed=True) is None


def test_a_label_that_fits_another_line_better_is_a_doubt_even_when_it_is_close_to_its_own():
    lines = {**LINES, "bs.cpltd": ["Current portion of long-term debt"]}
    doubt = mapping_doubt("Current portion of long-term debt", "bs.long_term_debt", lines)
    assert doubt and "bs.cpltd" in doubt


def test_reads_as_names_the_other_line_only_when_the_label_clearly_names_it():
    assert reads_as("Accounts payable", "bs.accrued_liabilities", LINES) == "bs.accounts_payable"
    assert reads_as("Accounts payable", "bs.accounts_payable", LINES) is None  # the line it was filed under
    assert reads_as("Trade creditors", "bs.accounts_payable", LINES) is None   # unfamiliar: names no line
    assert reads_as("  ", "bs.revolver", LINES) is None
    # the doubt and the line it names never disagree
    for label, assigned in (("Accounts payable", "bs.accrued_liabilities"), ("Line of credit", "bs.accounts_payable")):
        assert f"reads as {reads_as(label, assigned, LINES)}, not {assigned}" in mapping_doubt(label, assigned, LINES)


def test_similarity_ignores_case_punctuation_and_filler_words():
    assert similarity("Accounts Payable", "accounts payable") == 1.0
    assert similarity("Cost of goods sold", "Cost of Goods Sold") == 1.0
    assert similarity("Other liabilities", "Accrued liabilities") < 0.5
    assert similarity("", "Cash") == 0.0
