"""Read-only document tools shared by agents: list, search and read the borrower's documents.
The borrower always comes from the run (its scope, or the borrower an earlier tool opened),
never from the model."""
import re
import uuid

from sqlalchemy import select

from app.agents.tools import Refusal, Tool, ToolContext, ToolInput
from app.domain.documents import Document, DocumentPage

SNIPPET = 320
MAX_HITS = 8


def borrower_in_scope(ctx: ToolContext) -> uuid.UUID:
    borrower_id = ctx.scope.borrower_id or ctx.state.get("borrower_id")
    if borrower_id is None:
        raise Refusal("no borrower is open; open a borrower first")
    return borrower_id if isinstance(borrower_id, uuid.UUID) else uuid.UUID(str(borrower_id))


def _document(ctx: ToolContext, reference: str) -> Document:
    try:
        doc = ctx.db.get(Document, uuid.UUID(reference))
    except ValueError:
        doc = None
    if doc is None or doc.borrower_id != borrower_in_scope(ctx):
        raise Refusal("no such document for this borrower")
    return doc


class NoInput(ToolInput):
    pass


def _list_documents(ctx: ToolContext, args: NoInput) -> dict:
    docs = ctx.db.execute(select(Document).where(Document.borrower_id == borrower_in_scope(ctx))
                          .order_by(Document.effective_date.nulls_last(), Document.period_end.nulls_last())).scalars()
    return {"documents": [{
        "document_id": str(d.id), "type": d.doc_type, "title": d.title, "pages": d.page_count,
        "period_end": d.period_end.isoformat() if d.period_end else None,
        "effective_date": d.effective_date.isoformat() if d.effective_date else None,
        "received_date": d.received_date.isoformat() if d.received_date else None} for d in docs]}


class SearchInput(ToolInput):
    query: str
    document_type: str | None = None


def _search_documents(ctx: ToolContext, args: SearchInput) -> dict:
    words = [w for w in re.findall(r"[A-Za-z0-9$%.,-]+", args.query.lower()) if len(w) > 2]
    if not words:
        raise Refusal("the query has no searchable words")
    query = select(DocumentPage, Document).join(Document, Document.id == DocumentPage.document_id).where(
        Document.borrower_id == borrower_in_scope(ctx), DocumentPage.has_text.is_(True))
    if args.document_type:
        query = query.where(Document.doc_type == args.document_type)
    scored = []
    for page, doc in ctx.db.execute(query).all():
        text = page.text.lower()
        score = sum(text.count(w) for w in words)
        if score and all(w in text for w in words[:3]):
            first = min((text.find(w) for w in words if w in text), default=0)
            start = max(0, first - SNIPPET // 3)
            snippet = re.sub(r"\s+", " ", page.text[start:start + SNIPPET]).strip()
            scored.append((score, {"document_id": str(doc.id), "type": doc.doc_type, "title": doc.title,
                                   "page": page.page_number, "snippet": snippet}))
    scored.sort(key=lambda item: -item[0])
    return {"hits": [hit for _, hit in scored[:MAX_HITS]], "total_pages_matching": len(scored)}


class ReadPageInput(ToolInput):
    document_id: str
    page: int


def _read_page(ctx: ToolContext, args: ReadPageInput) -> dict:
    doc = _document(ctx, args.document_id)
    page = ctx.db.execute(select(DocumentPage).where(
        DocumentPage.document_id == doc.id, DocumentPage.page_number == args.page)).scalar_one_or_none()
    if page is None:
        raise Refusal(f"{doc.title} has {doc.page_count} pages")
    if not page.has_text:
        raise Refusal("this page is an image with no readable text")
    return {"document_id": str(doc.id), "title": doc.title, "page": page.page_number, "text": page.text}


LIST_DOCUMENTS = Tool("list_documents", "List the documents on file for the borrower.", NoInput, _list_documents)
SEARCH_DOCUMENTS = Tool(
    "search_documents",
    "Search the text of the borrower's documents for words or a phrase. Returns pages with a snippet. "
    "Optionally limit to one document type (credit_agreement, amendment, compliance_certificate, ...).",
    SearchInput, _search_documents)
READ_PAGE = Tool("read_page", "Read the full text of one page of one of the borrower's documents.",
                 ReadPageInput, _read_page)
DOCUMENT_TOOLS = (LIST_DOCUMENTS, SEARCH_DOCUMENTS, READ_PAGE)
