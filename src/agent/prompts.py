"""
EchoAgent — Conversation Prompts and Curated Question Bank
Categorized by target vocal characteristics to maximize acoustic diversity during the 120s session.
"""

SYSTEM_PROMPT = """You are EchoAgent, an empathetic, curious voice conversationalist.
Your goal is to engage the user in a natural, lively conversation for 120 seconds.
Ask questions that encourage full sentences, varied emotional inflections, and authentic vocal prosody.
Keep each response concise (1-2 sentences maximum) so the user does most of the speaking.
"""

CURATED_QUESTIONS: list[dict[str, str]] = [
    {
        "id": "q1",
        "category": "emotional",
        "question": "What is one memory from your childhood that always brings an instant smile to your face?",
        "target": "warmth_pitch_variation",
    },
    {
        "id": "q2",
        "category": "descriptive",
        "question": "If you close your eyes right now, can you describe your favorite place in nature that brings you peace?",
        "target": "steady_prosody_detail",
    },
    {
        "id": "q3",
        "category": "imaginative",
        "question": "If you could step into a time machine and live in any century for just one week, where and when would you go?",
        "target": "vocal_inflection_excitement",
    },
    {
        "id": "q4",
        "category": "passionate",
        "question": "What is something you could talk about for hours without ever getting bored?",
        "target": "energetic_tempo_flow",
    },
    {
        "id": "q5",
        "category": "reflective",
        "question": "What is the best piece of advice anyone has ever given you that actually changed how you think?",
        "target": "calm_cadence_pause",
    },
    {
        "id": "q6",
        "category": "imaginative",
        "question": "If you had the power to invent any machine tomorrow to help humanity, what would it do?",
        "target": "creative_inflection",
    },
    {
        "id": "q7",
        "category": "descriptive",
        "question": "Tell me about the most unforgettable meal you have ever had. What made it so special?",
        "target": "sensory_prosody",
    },
]

