"""Exact code-point slices into immutable normalized source text."""


def slices(text: str, size: int = 2000) -> list[tuple[int, int, str]]:
    result = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        result.append((start, end, text[start:end]))
        start = end
    return result
