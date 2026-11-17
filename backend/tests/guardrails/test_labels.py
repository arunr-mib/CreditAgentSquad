from app.guardrails.labels import mapping_doubt, similarity

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


def test_the_right_line_and_an_unfamiliar_label_raise_nothing():
    assert mapping_doubt("Long-term debt, net of current portion", "bs.long_term_debt", LINES) is None
    assert mapping_doubt("Accounts payable", "bs.accounts_payable", LINES) is None
    # a borrower's own wording that matches no known line is left to the footing checks
    assert mapping_doubt("Notes payable to bank", "bs.revolver", LINES) is None
    assert mapping_doubt("Trade creditors", "bs.accounts_payable", LINES) is None
    # a near label that is closer to the assigned line than to any other is fine
    assert mapping_doubt("Long-term debt", "bs.long_term_debt", LINES) is None


def test_similarity_ignores_case_punctuation_and_filler_words():
    assert similarity("Accounts Payable", "accounts payable") == 1.0
    assert similarity("Cost of goods sold", "Cost of Goods Sold") == 1.0
    assert similarity("Other liabilities", "Accrued liabilities") < 0.5
    assert similarity("", "Cash") == 0.0
