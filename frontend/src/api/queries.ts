/**
 * Data access for the workspace. Slice one runs on typed fixtures; each hook keeps one query per
 * screen so that swapping `queryFn` for calls to /api/v1 is the only change needed later.
 *
 * Fixture shape -> real endpoint (backend/app/api/routes_credit.py, routes_work.py). Not wired yet.
 *
 * useWorkQueue
 *   items[]            -> GET /work-items (list omits evidence, recommendation, guardrail_notes;
 *                         fetch GET /work-items/{id} when a row is selected)
 *     type             -> item_type          summary        -> title
 *     dueDate          -> due_date           decisions[]    -> allowed_decisions (string[]; labels and
 *     requiresSecondPerson -> requires_second_person           the primary choice are chosen client-side)
 *     recommendation.guardrailNotes -> guardrail_notes (on the item, not inside recommendation)
 *   facts              -> GET /facts/{id} per referenced fact (no bulk endpoint yet)
 *   summary            -> no endpoint; derive from GET /cycles, GET /work-items, GET /calendar
 *
 * useCovenantWorkspace
 *   borrower           -> GET /borrowers/{id} (relationship_manager, analyst, facilities[]; say "loan" in the interface)
 *   cycle.stages[]     -> GET /cycles/{id} .stages[] (stage, position, status, detail, open_work_items)
 *   covenants[]        -> GET /borrowers/{id}/covenant-tests
 *     calculatedFactId -> value_fact_id      certificateFactId -> reported_fact_id
 *     thresholdFactId  -> threshold is a plain value, with no fact id: needs a cited terms fact to keep its glyph
 *     headroomFactId   -> headroom_pct is a plain value on the test; source is the test's calc_run_id
 *   breakdowns         -> GET /covenant-tests/{id} .calculation (inputs, outputs, trace); rows are built client-side
 *   trend              -> the same list, earlier period_end values
 *
 * useSpread
 *   periods[], sections[].lines[].cells -> GET /borrowers/{id}/spread
 *     (periods[{period_end, months}]; lines[{key, label, statement, computed, cells{period_end: {fact_id, value, kind, status, usable}}}])
 *     quality, spreadStatus, stated totals and subtotal/total emphasis are not in the response yet
 *   facts[id].provenance -> GET /facts/{id}: flat columns (kind, document_id, page, quote, label_text,
 *     scale_as_reported, calc_run_id + calculation, connector, record_ref, as_of, entered_by, reason).
 *     Kind "seeded" has no glyph yet. `printed` (the figure as printed) is not a column.
 *   sourcePages        -> GET /documents/{id}/pages/{n} (the facsimile stands in for the real page)
 *
 * Shell: simulated date -> GET/POST /clock ({today}). Identifiers are UUIDs in the API; fixtures use short readable ids.
 */
import { useQuery } from '@tanstack/react-query';
import * as brightwater from '@/fixtures/brightwater';
import { portfolioSummary, workItemFacts, workItems } from '@/fixtures/workItems';

export function useWorkQueue() {
  return useQuery({
    queryKey: ['work-queue'],
    queryFn: async () => ({ items: workItems, facts: workItemFacts, summary: portfolioSummary }),
  });
}

export function useCovenantWorkspace(borrowerId: string) {
  return useQuery({
    queryKey: ['covenant-workspace', borrowerId],
    queryFn: async () => ({
      borrower: brightwater.borrower,
      cycle: brightwater.cycle,
      covenants: brightwater.covenants,
      breakdowns: brightwater.breakdowns,
      trend: brightwater.fccrTrend,
      workItem: brightwater.fccrWorkItem,
      named: brightwater.named,
      facts: brightwater.facts,
    }),
  });
}

export function useSpread(borrowerId: string) {
  return useQuery({
    queryKey: ['spread', borrowerId],
    queryFn: async () => ({
      borrower: brightwater.borrower,
      periods: brightwater.periods,
      sections: brightwater.spreadSections,
      footingChecks: brightwater.footingChecks,
      sourcePages: brightwater.sourcePages,
      facts: brightwater.facts,
      notice: brightwater.SYNTHETIC_NOTICE,
    }),
  });
}
