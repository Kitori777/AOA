from __future__ import annotations


def render_user_summary(title: str, bullets: list[str]) -> str:
    lines = [title.strip(), "=" * max(10, len(title.strip()))]
    for bullet in bullets:
        if bullet.strip():
            lines.append(f"- {bullet.strip()}")
    return "\n".join(lines)
