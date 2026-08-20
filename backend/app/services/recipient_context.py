from app.schemas import ContactCreate

TONE_STYLE_INSTRUCTIONS = {
    "polite_concise": (
        "Use courteous professional language, concise sentences, and clear requests. "
        "Avoid unnecessary greetings, repetition, slang, and overly elaborate phrasing."
    ),
    "friendly_professional": (
        "Use a warm, approachable, collaborative voice while remaining professional. "
        "Prefer natural conversational wording and soften commands into friendly requests."
    ),
    "formal_official": (
        "Use formal, official business language with respectful titles and complete sentences. "
        "Avoid contractions, casual expressions, slang, and overly familiar wording."
    ),
    "warm_persuasive": (
        "Use a considerate, positive, and gently persuasive voice. Explain benefits clearly, "
        "use tactful requests, and avoid pressure, exaggeration, or manipulative language."
    ),
}


def build_recipient_context(contact: ContactCreate | None) -> dict[str, object] | None:
    if contact is None:
        return None

    return {
        "name": contact.name,
        "organization": contact.company,
        "position": contact.role,
        "country": contact.country,
        "tone_style": contact.tone_style,
        "tone_instruction": TONE_STYLE_INSTRUCTIONS[contact.tone_style],
        "communication_preferences": contact.communication_preferences or contact.note,
        "required_behavior": [
            "Treat this person as the intended recipient, not the author or logged-in user.",
            "Follow tone_instruction and communication_preferences in word choice and sentence style.",
            "Use an appropriate level of title, honorific, directness, and formality for their position and country.",
            "Do not mention or explain the profile in the translated output.",
            "Do not invent a greeting, title, relationship, or fact that is absent from the source or preferences.",
        ],
    }
