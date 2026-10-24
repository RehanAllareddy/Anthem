"""Fixed lyric templates, one per beat category, used when Claude isn't configured.

Every song in a category gets the same lines with the listener's details filled in:
  {name}     their name or nickname
  {hobby1}   first hobby
  {hobby2}   second hobby
  {hobby3}   third hobby, or "{hobby1} and {hobby2}" when they gave only two
  {message}  what they want to hear, e.g. "you've got this"

Hobbies are free text ("drawing", "soccer", "my dog"), so they only appear in
phrasings that read naturally with any noun: "lost in {hobby}", "from {hobby1} to
{hobby2}", "think of {hobby}". Keep that in mind when editing.
"""
from __future__ import annotations

from typing import Dict, List

TEMPLATES: Dict[str, Dict[str, object]] = {
    "pop": {
        "title": "Brighter Than You Know",
        "verse1": [
            "Hey {name}, I know the days get heavy",
            "Like the world is spinning way too fast",
            "But you shine when you're lost in {hobby1}",
            "And that kind of light is built to last",
            "From {hobby2} to the little things you love",
            "You remember who you really are",
            "So breathe in slow and let the noise get quiet",
            "Look how you have come so far",
        ],
        "chorus": [
            "{name}, you are amazing",
            "Brighter than you know",
            "Hear me say {message}",
            "This is your time to glow",
        ],
        "verse2": [
            "When the doubts come knocking at your door",
            "You don't have to let them in",
            "Think of {hobby3} and the joy it brings",
            "That's the spark that's always been within",
            "Every step you take is still a step",
            "Even slow is moving on",
            "You don't have to get it perfect",
            "You just have to carry on",
        ],
    },
    "upbeat": {
        "title": "Turn It Up for {name}",
        "verse1": [
            "Wake up {name}, the sun is calling",
            "Shake off yesterday, it's a brand new start",
            "Got {hobby1} on my mind and the beat is rolling",
            "Got a rhythm running right through your heart",
            "Hands up high if you're feeling stronger",
            "From {hobby2} to the things you do",
            "Every day you shine a little longer",
            "The whole world's better because of you",
        ],
        "chorus": [
            "{name}, you are amazing",
            "Turn it up, turn it up",
            "Hear me say {message}",
            "You were made to light it up",
        ],
        "verse2": [
            "When the pressure's piling up like thunder",
            "Take a breath and let it roll away",
            "Think of {hobby3}, all the joy and wonder",
            "Dance it out and own the day",
            "You don't need to be perfect, no",
            "You just need to be you",
            "Every little win is worth a celebration",
            "And you've got so many coming through",
        ],
    },
    "chill": {
        "title": "Slow Breath, {name}",
        "verse1": [
            "Easy now {name}, breathe in slow",
            "Let your shoulders fall, let the worry go",
            "Think of {hobby1}, soft and warm",
            "A quiet place inside the storm",
            "There's no rush and there's no race",
            "Just the calm in this small space",
            "With {hobby2} and the things you love",
            "You are more than enough",
        ],
        "chorus": [
            "{name}, you are amazing",
            "Just breathe, just be",
            "Hear me say {message}",
            "Let this moment set you free",
        ],
        "verse2": [
            "Like the tide that comes back in",
            "Every hard day has an end",
            "Find some peace in {hobby3}",
            "Be gentle, be your own best friend",
            "Rest is not a thing you earn",
            "It's a gift you get to keep",
            "Tomorrow's light will come again",
            "For now, just breathe",
        ],
    },
    "rap": {
        "title": "{name}'s Rise",
        "verse1": [
            "Yo {name}, listen up, this one's for you",
            "Every single step you take, you're breaking through",
            "Head full of {hobby1}, got a vision that's true",
            "Got a fire in your chest that the doubt can't subdue",
            "They don't see the work, but I know what you do",
            "From {hobby2} to the dreams that you're building too",
            "When the pressure gets loud, you just stay in your groove",
            "And you rise every time, that's the proof",
        ],
        "chorus": [
            "{name}, you are amazing",
            "Stand tall, stand proud",
            "Hear me say {message}",
            "Let them hear it loud",
        ],
        "verse2": [
            "Stress tried to stack up like a wall in the way",
            "But you climb it one brick at a time every day",
            "Keep {hobby3} in your heart, let it carry the weight",
            "You're the author of the story, you control the pace",
            "Ain't no shame in a pause, ain't no shame in a break",
            "Every legend needs a breath before the next take",
            "So remember who you are when the doubts come to play",
            "You were born to shine bright and you're here to stay",
        ],
    },
    "rock": {
        "title": "Unbreakable",
        "verse1": [
            "Hey {name}, they can't hold you down",
            "Got thunder in your heart and you won't back down",
            "Got {hobby1} in your blood and it's loud and proud",
            "You're the spark in the dark, you're the light in the crowd",
            "When the walls close in and the night feels long",
            "Hold on to {hobby2} and sing your song",
            "Every scar's a story that made you strong",
            "And you've known it all along",
        ],
        "chorus": [
            "{name}, you are amazing",
            "Unbreakable, unstoppable",
            "Hear me say {message}",
            "Nothing is impossible",
        ],
        "verse2": [
            "So raise your voice and shake the ground",
            "Let the doubt fall away with every sound",
            "With {hobby3} and the fire you've found",
            "You're the kind of strong that won't burn out",
            "Take a breath, it's okay to rest",
            "Even heroes need to catch their breath",
            "Tomorrow you'll be back at your best",
            "So stand up tall, you've passed the test",
        ],
    },
}


def fill(category: str, name: str, hobbies: List[str], message: str) -> Dict[str, object]:
    """Return {"title", "verse1", "chorus", "verse2"} with the listener's details filled in."""
    template = TEMPLATES.get(category, TEMPLATES["pop"])
    hobby3 = hobbies[2] if len(hobbies) > 2 else f"{hobbies[0]} and {hobbies[1]}"
    values = {"name": name, "hobby1": hobbies[0], "hobby2": hobbies[1], "hobby3": hobby3, "message": message}

    def sub(line: str) -> str:
        # str.format_map would choke on braces typed into a hobby; replace placeholders explicitly.
        for key, value in values.items():
            line = line.replace("{" + key + "}", value)
        return line

    return {
        "title": sub(template["title"]),  # type: ignore[arg-type]
        **{part: [sub(l) for l in template[part]] for part in ("verse1", "chorus", "verse2")},  # type: ignore[union-attr]
    }
