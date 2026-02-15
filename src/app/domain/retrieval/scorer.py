def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def sparse_score(query: str, doc: str) -> float:
    q_tokens = set(query.split())
    d_tokens = set((doc or "").lower().split())
    if not q_tokens:
        return 0.0
    return len(q_tokens.intersection(d_tokens)) / len(q_tokens)


def hybrid_score(sparse: float, dense: float, w_sparse: float = 0.45, w_dense: float = 0.55) -> float:
    return w_sparse * sparse + w_dense * dense
