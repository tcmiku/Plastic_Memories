from ..interfaces import ProfileBuilder


class MarkdownProfileBuilder:
    def build(self, persona: dict | None, memory_items) -> str:
        lines = ["# Persona Profile"]
        if persona:
            lines.append(f"- User: {persona['user_id']}")
            lines.append(f"- Persona: {persona['persona_id']}")
            if persona.get("display_name"):
                lines.append(f"- Name: {persona['display_name']}")
            if persona.get("description"):
                lines.append(f"- Description: {persona['description']}")
        if memory_items:
            lines.append("")
            lines.append("## Memory Items")
            for item in memory_items:
                lines.append(f"- [{item['type']}] {item['mkey']}: {item['content']}")
        return "\n".join(lines)
