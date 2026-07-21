from __future__ import annotations

import math
from collections import Counter
from itertools import combinations


def bundle_metrics(
    extractions: list[dict[str, object]], min_pair_support: int = 1
) -> dict[str, object]:
    skills = [str(item["skill_id"]) for item in extractions]
    categories = [str(item["analysis_category_code"]) for item in extractions]
    skill_counts = Counter(skills)
    category_counts = Counter(categories)
    total = len(categories)
    probs = [count / total for count in category_counts.values()] if total else []
    entropy = -sum(prob * math.log(prob) for prob in probs if prob > 0)
    hhi = sum(prob * prob for prob in probs)
    pair_counts = Counter(
        "__".join(sorted(pair)) for pair in combinations(set(categories), 2)
    )
    return {
        "mention_count": total,
        "unique_skill_count": len(skill_counts),
        "unique_category_count": len(category_counts),
        "category_counts": dict(category_counts),
        "breadth": len(category_counts),
        "skill_breadth": len(skill_counts),
        "category_entropy": entropy,
        "category_hhi": hhi,
        "pair_support": {
            pair: count
            for pair, count in pair_counts.items()
            if count >= min_pair_support
        },
    }


def corpus_metrics(
    documents: list[list[dict[str, object]]], min_support: int = 2
) -> dict[str, object]:
    document_count = len(documents)
    document_skill_counts = Counter()
    document_category_counts = Counter()
    pair_documents = Counter()
    for document in documents:
        skills = {str(item["skill_id"]) for item in document}
        categories = {str(item["analysis_category_code"]) for item in document}
        for skill in skills:
            document_skill_counts[skill] += 1
        for category in categories:
            document_category_counts[category] += 1
        for pair in combinations(sorted(categories), 2):
            pair_documents["__".join(pair)] += 1
    rarity = {
        skill: math.log((document_count + 1) / (count + 1))
        for skill, count in document_skill_counts.items()
    }
    npmi = {}
    for pair, count in pair_documents.items():
        if count < min_support or not document_count:
            continue
        left, right = pair.split("__", 1)
        p_xy, p_x, p_y = (
            count / document_count,
            document_category_counts[left] / document_count,
            document_category_counts[right] / document_count,
        )
        pmi = math.log(p_xy / (p_x * p_y)) if p_x and p_y else 0.0
        npmi[pair] = pmi / (-math.log(p_xy)) if p_xy not in (0, 1) else 1.0
    return {
        "documents": document_count,
        "skill_document_counts": dict(document_skill_counts),
        "rarity": rarity,
        "npmi": npmi,
    }
