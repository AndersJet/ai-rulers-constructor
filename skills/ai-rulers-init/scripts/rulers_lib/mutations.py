"""One transaction boundary shared by public lifecycle writers."""
from __future__ import annotations

import functools
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .paths import resolve_layout
from .transactions import file_transaction


CURRENT = ContextVar("rulers_transaction", default=None)
CURRENT_ID = ContextVar("rulers_transaction_id", default=None)


@contextmanager
def mutation(layout, *, transaction_id=None):
    if CURRENT.get() is not None:
        raise ValueError("Nested rulers writes require one explicit transaction boundary")
    identifier = transaction_id or uuid.uuid4().hex[:16]
    with file_transaction(layout=layout, plan_id=identifier) as transaction:
        token = CURRENT.set(transaction)
        id_token = CURRENT_ID.set(identifier)
        try:
            yield transaction
        finally:
            CURRENT.reset(token)
            CURRENT_ID.reset(id_token)


def write_text(path: Path, text: str) -> None:
    transaction = CURRENT.get()
    if transaction is None:
        raise ValueError("Rulers writes must run inside a transaction")
    transaction.replace_bytes(path.relative_to(transaction._layout.project_root), text.encode("utf-8"))


def transactional(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        layout = resolve_layout(kwargs["project_root"], kwargs["rulers_dir"])
        with mutation(layout):
            return function(*args, **kwargs)
    return wrapped
