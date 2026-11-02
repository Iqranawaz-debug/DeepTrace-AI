"""Tavily is disabled. Test doubles return explicitly simulated leads only."""

from deeptrace.providers import OutboundDisabled, SearchRequest, SearchResult


class Tavily:
    def search(self, request: SearchRequest) -> list[SearchResult]:
        raise OutboundDisabled("Live Tavily integration is not authorized")


class MockTavily:
    def search(self, request: SearchRequest) -> list[SearchResult]:
        return [SearchResult(title="SIMULATED search lead", url="https://fixture.example/article")][
            : request.limit
        ]
