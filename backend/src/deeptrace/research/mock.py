"""Deterministic simulated adapters satisfying the live contracts. Never touch a network."""

import hashlib
import json
import re

from deeptrace.research.contracts import LLMText, SearchLead

CATALOG = ("lead-1", "lead-2", "blocked", "lead-3", "failure", "injection")
_PASSAGE = re.compile(r"<<<PASSAGE id=(P-\d+) source=[^\n]*>>>\n(.*?)\n<<<END PASSAGE>>>", re.S)
_QUESTION = re.compile(r"<<<QUESTION>>>\n(.*?)\n<<<END QUESTION>>>", re.S)


class MockSearch:
    id = "mock_search"

    def search(self, query: str, limit: int, timeout: float) -> list[SearchLead]:
        start = hashlib.sha256(query.encode()).digest()[0] % len(CATALOG)
        names = [CATALOG[(start + i) % len(CATALOG)] for i in range(min(limit, len(CATALOG)))]
        return [
            SearchLead(f"https://fixture.example/{name}", f"SIMULATED lead {name}", rank)
            for rank, name in enumerate(names, 1)
        ]


class MockLLM:
    id = "mock_llm"
    model = "mock-deterministic-v1"

    def generate(self, prompt: str, max_tokens: int, timeout: float) -> LLMText:
        question = _QUESTION.search(prompt)
        subject = " ".join((question.group(1) if question else "").split())
        # Only the synthesis template contains this marker; question text is neutralized.
        text = self._synthesize(prompt) if "<<<PASSAGE" in prompt else self._plan(subject)
        return LLMText(text, None, None)

    @staticmethod
    def _plan(subject: str) -> str:
        short = subject[:400]
        if len(subject.split()) <= 3:
            steps = [{"sub_question": f"What does {short} refer to?", "search_query": short}]
            return json.dumps(
                {"steps": steps, "narrow_reason": "The question is narrow; one step is enough."}
            )
        angles = ("Background", "Current evidence", "Conflicting findings", "Open questions")
        steps = [
            {"sub_question": f"SIMULATED {angle} for: {short}", "search_query": f"{short} {angle}"}
            for angle in angles
        ]
        return json.dumps({"steps": steps, "narrow_reason": None})

    @staticmethod
    def _synthesize(prompt: str) -> str:
        claims = []
        for display, text in _PASSAGE.findall(prompt):
            words = " ".join(text.split()[:6])
            quote = words if words in " ".join(text.split()) else None
            claims.append(
                {
                    "text": f"SIMULATED claim drawn from fixture passage {display}.",
                    "citations": [{"passage_id": display, "quote": quote}],
                }
            )
        claims.append(
            {
                "text": "SIMULATED: these fixtures establish no real-world conclusion.",
                "citations": [],
            }
        )
        return json.dumps(
            {
                "summary": "SIMULATED summary produced by the deterministic mock model.",
                "claims": claims[:20],
                "limitations": "All passages are synthetic fixtures. No real research occurred.",
                "needed_evidence": "Real sources would be required to answer this question.",
            }
        )
