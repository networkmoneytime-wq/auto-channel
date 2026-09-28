"""An original cast of anthropomorphized food characters for the meme channel's
"DRAMA" format -- short, over-the-top soap-opera scenes (cheating, jealousy,
a dramatic reveal) narrated like a reality-TV voiceover. This is the format
the user asked for after seeing "the fruit where they cheat on each other"
trend: same general genre (anthropomorphized food, melodrama), but every
name, personality, and visual design here is original to this project, not
copied from any specific existing creator's characters or storylines -- the
genre itself isn't ownable, a specific creator's specific cast is.

A small fixed roster (not a new character invented every video) so the
channel builds a recognizable, recurring cast the way the real trend does --
script_gen_meme.py's DRAMA generator draws two of these per video rather
than asking the LLM to invent characters from scratch.

The "visual" fields deliberately stick to neutral, pose-based description
(the same style already proven to render cleanly for the real characters in
brainrot_characters.py) rather than emotionally-loaded facial-expression
language: the first version of this roster described faces as "glaring",
"smug", with "narrowed scheming eyes", and Cloudflare Workers AI's image
model rejected two different characters in the same real run as NSFW content
-- a false positive (there's nothing actually explicit about a cartoon
pineapple), but a real, repeatable one, the same false-positive-on-wording
class of issue brainrot_characters.py already documented for character
names specifically. Neutral wording renders without tripping it."""

CHARACTERS = [
    {
        "name": "Peaches",
        "personality": "The emotional center of every storyline. Sweet, dramatic, and always \"just found out\" something devastating.",
        "visual": "a peach character with cartoon arms and legs, one hand on its chest, dramatic pose, soft pink lighting, photorealistic 3D render, plain background",
    },
    {
        "name": "Mango Marco",
        "personality": "A smooth-talking charmer. Confident, a little smug, and somehow the third point in every love triangle.",
        "visual": "a mango character with cartoon arms and legs wearing sunglasses and a gold chain, standing pose, photorealistic 3D render, plain background",
    },
    {
        "name": "Pineapple Percy",
        "personality": "Spiky attitude to match the exterior. Loyal, quick to anger, terrible at staying quiet about a grudge.",
        "visual": "a pineapple character with cartoon arms and legs, spiky leaves styled like hair, arms crossed, standing pose, photorealistic 3D render, plain background",
    },
    {
        "name": "Bananarama",
        "personality": "Chaotic and can't keep a secret for five minutes. The reason everyone always finds out everything.",
        "visual": "a banana character with cartoon arms and legs, peel open like a flowing dress, comedic pose with one hand near its mouth, photorealistic 3D render, plain background",
    },
    {
        "name": "Coco Nutt",
        "personality": "Hard shell, soft center. Everyone's go-to for advice, despite secretly having the messiest personal life of the group.",
        "visual": "a coconut character with cartoon arms and legs wearing small round glasses, calm pose holding a clipboard, photorealistic 3D render, plain background",
    },
    {
        "name": "Strawberry Shay",
        "personality": "Sweet on the outside. Actually the quiet mastermind behind half the group's drama.",
        "visual": "a strawberry character with cartoon arms and legs, sweet smile, hands clasped together, standing pose, photorealistic 3D render, plain background",
    },
    {
        "name": "Big Kiwi",
        "personality": "Blunt, zero patience for nonsense, always the one who says what everyone else is only thinking.",
        "visual": "a kiwi fruit character with cartoon arms and legs, stocky build, arms crossed, standing pose, photorealistic 3D render, plain background",
    },
    {
        "name": "The Grapes",
        "personality": "A gossiping cluster who react to everyone else's drama like a Greek chorus. Never the center of the story, always narrating it.",
        "visual": "a cluster of grape characters each with tiny cartoon faces, huddled together, comedic pose, photorealistic 3D render, plain background",
    },
]
