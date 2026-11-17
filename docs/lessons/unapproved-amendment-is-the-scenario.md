In test data, an amendment that is on file but not approved into terms is the scenario itself; approving it in a seed or fixture removes what the agent is meant to find.

Inherited from CreditScout. Rule: synthetic scenarios that depend on terms lag must keep the amendment out of the approved terms, and a test should fail if a seed approves it.

Applies to: `synthetic/` scenarios and database seeds.
