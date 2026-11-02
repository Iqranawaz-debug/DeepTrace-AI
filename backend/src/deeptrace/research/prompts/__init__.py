"""Version-controlled prompt templates. Retrieved content stays outside trusted instructions."""

from pathlib import Path

PLAN_VERSION = "plan-v1"
SYNTHESIZE_VERSION = "synthesize-v1"
_HERE = Path(__file__).parent


def neutralize(text: str) -> str:
    """Untrusted text must not be able to close or forge a delimiter."""
    return text.replace("<<<", "‹‹‹").replace(">>>", "›››")


def plan_prompt(question: str) -> str:
    template = (_HERE / "plan_v1.txt").read_text(encoding="utf-8")
    return template.replace("{question}", neutralize(question))


def synthesize_prompt(question: str, passages: list[tuple[str, str, str]]) -> str:
    """Passages are (display id, source title, text)."""
    blocks = [
        f"<<<PASSAGE id={display} source={neutralize(title)}>>>\n{neutralize(text)}\n"
        "<<<END PASSAGE>>>"
        for display, title, text in passages
    ]
    template = (_HERE / "synthesize_v1.txt").read_text(encoding="utf-8")
    return template.replace("{question}", neutralize(question)).replace(
        "{passages}", "\n".join(blocks)
    )
