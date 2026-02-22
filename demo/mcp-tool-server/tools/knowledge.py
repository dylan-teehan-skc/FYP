"""Knowledge base tool: search_knowledge_base."""

from data import KNOWLEDGE_BASE


def search_knowledge_base(arguments: dict, state) -> dict:
    query = arguments.get("query", "").lower()
    if not query:
        return {"error": "Search query cannot be empty"}

    query_words = query.split()
    results = []

    for article in KNOWLEDGE_BASE.values():
        score = 0
        for word in query_words:
            if word in article["title"].lower():
                score += 2
            for kw in article["keywords"]:
                if word in kw:
                    score += 1
            if word in article["content"].lower():
                score += 1
        if score > 0:
            results.append((score, article))

    results.sort(key=lambda x: x[0], reverse=True)

    matched = [
        {
            "article_id": article["article_id"],
            "title": article["title"],
            "content": article["content"],
        }
        for _, article in results[:3]
    ]

    return {
        "query": query,
        "results_count": len(matched),
        "results": matched,
    }
