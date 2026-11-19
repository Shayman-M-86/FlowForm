"""Returning an overwritten answer must refresh its already-loaded ORM instance."""

from uuid import uuid4

from pydantic import TypeAdapter
from sqlalchemy import MetaData, Table, create_engine, select
from sqlalchemy.orm import Session

from app.repositories.response import response_answer_repo
from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.schema.types import AnswerLocator, ClientMutationId


def test_upsert_refreshes_existing_ciphertext_mutation_and_saved_timestamp():
    metadata = MetaData()
    for model in (ResponseEnvelope, ResponseAnswer):
        table = model.__table__
        assert isinstance(table, Table)
        table.to_metadata(metadata)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    envelope_id = uuid4()
    locator = AnswerLocator(b"a" * 32)
    first_mutation = TypeAdapter(ClientMutationId).validate_python(uuid4())
    second_mutation = TypeAdapter(ClientMutationId).validate_python(uuid4())
    try:
        metadata.create_all(engine)
        with Session(engine) as db:
            db.execute(
                metadata.tables["response_envelopes"]
                .insert()
                .values(
                    id=envelope_id,
                    session_locator=b"s" * 32,
                    linkage_key_version=1,
                    wrapped_session_dek=b"wrapped",
                    crypto_version=1,
                )
            )
            first = response_answer_repo.upsert_current(
                db,
                envelope_id=envelope_id,
                answer_locator=locator,
                ciphertext=b"first",
                nonce=b"1" * 12,
                client_mutation_id=first_mutation,
            )
            assert first.ciphertext == b"first"
            second = response_answer_repo.upsert_current(
                db,
                envelope_id=envelope_id,
                answer_locator=locator,
                ciphertext=b"second",
                nonce=b"2" * 12,
                client_mutation_id=second_mutation,
            )
            assert second is first
            assert second.ciphertext == b"second" and second.client_mutation_id == second_mutation
            assert second.updated_at == db.scalar(select(ResponseAnswer.updated_at))
            assert len(list(db.scalars(select(ResponseAnswer)))) == 1
    finally:
        engine.dispose()
