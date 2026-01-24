from app.infrastructure.repositories.idempotency_repo import IdempotencyRepository


def test_hash_payload_consistent():
    payload = {"a": 1, "b": 2}
    h1 = IdempotencyRepository._hash_payload(payload)
    h2 = IdempotencyRepository._hash_payload({"b": 2, "a": 1})
    assert h1 == h2


def test_hash_payload_different_for_changed_payload():
    a = {"a": 1}
    b = {"a": 2}
    assert IdempotencyRepository._hash_payload(
        a
    ) != IdempotencyRepository._hash_payload(b)
