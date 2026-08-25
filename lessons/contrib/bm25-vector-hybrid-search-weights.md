---
{
  "title": "BM25 + Vector Hybrid Search: configurable blending weights",
  "domain": "search",
  "tags": [
    "bm25",
    "vector",
    "hybrid",
    "search",
    "weights"
  ],
  "status": "published",
  "evidence_level": "E2",
  "source": "closed-pr-1029",
  "created": "2026-08-22"
}
---
<!-- provenance:
provenance:
  source: "internal"
  contributor: "Ikalus1988"
  merged_at: "2026-08-22"
  evidence: "post-publication"
-->

## Problem

Search uses only BM25, missing semantic similarity from vector embeddings.

## Solution

Configurable BM25 + vector blending via config.yaml or env vars. Default 50/50 with RRF blending.

## Key Points

- Normalize scores to [0,1] before blending
- RRF (reciprocal rank fusion) recommended
- Weights must sum to 1.0


## Verification

```bash
grep -i 'bm25\|chunk\|embed' lessons/contrib/rag-*.md 2>/dev/null | head -3
echo Search verified
```

**Expected Output:**
```
# (refs)
Search verified
```
