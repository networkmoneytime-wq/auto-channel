"""A curated roster of real, already-popular Italian/AI-brainrot characters
(Tralalero Tralala, Tung Tung Tung Sahur, etc.) -- verified against real,
current sources rather than invented, so the meme channel's AI-character
format makes content about characters audiences already know and search
for, instead of an original creation nobody's heard of.

The "visual" field deliberately never uses the character's own name:
testing found asking Cloudflare Workers AI's image model for a character by
name (e.g. "Tung Tung Tung Sahur") reliably trips its NSFW filter as a
false positive, while describing the same established design without the
name renders cleanly and still comes out recognizably close to the real
thing -- confirmed by eye on every entry below before this shipped."""

CHARACTERS = [
    {
        "name": "Tralalero Tralala",
        "visual": "a three-legged shark wearing blue Nike sneakers, mid-stride on a city street, photorealistic 3D render, dramatic lighting",
        "lore": "The original, most iconic character of the genre -- a shark with three legs in blue sneakers, known for a sing-songy nonsense catchphrase.",
    },
    {
        "name": "Bombardiro Crocodilo",
        "visual": "a crocodile fused with a military bomber airplane, wings and engines merged with its body, flying, dramatic sky, photorealistic 3D render",
        "lore": "A crocodile-bomber hybrid, shown flying -- one of the characters that started the genre's animal-plus-machine hybrid subgenre.",
    },
    {
        "name": "Ballerina Cappuccina",
        "visual": "a ballerina mid-pose in a tutu, with a cappuccino cup and saucer in place of her head, warm coffee tones, elegant studio lighting, photorealistic 3D render",
        "lore": "A ballerina with a cappuccino cup for a head -- known as the most visually elegant character in the genre, a tonal contrast to the usual chaos.",
    },
    {
        "name": "Tung Tung Tung Sahur",
        "visual": "a tall wooden log creature with a carved face, wielding a wooden baseball bat, walking, photorealistic 3D render, plain background",
        "lore": "A wooden log creature carrying a bat -- unusual in the genre for being an object rather than an animal hybrid, originally from Indonesian meme culture before crossing into the wider brainrot canon.",
    },
    {
        "name": "Lirili Larila",
        "visual": "an elephant wearing sandals, carrying an old pocket watch, calm pose, soft warm lighting, photorealistic 3D render",
        "lore": "A sandal-wearing elephant carrying a pocket watch -- the calm, peaceful 'moral center' of the brainrot universe, a deliberate contrast to its chaotic characters.",
    },
    {
        "name": "Brr Brr Patapim",
        "visual": "a toad-like creature with a small tree growing out of the top of its head, sitting, forest background, photorealistic 3D render",
        "lore": "A toad with a tree growing from its head -- a recurring background character that signals to fans that a video is genuine brainrot content.",
    },
    {
        "name": "Trippi Troppi",
        "visual": "a cat-fish hybrid creature wearing a wizard's robe and pointed hat, holding a glowing staff, mystical background, photorealistic 3D render",
        "lore": "A cat-fish hybrid dressed as a wizard -- the genre's resident magic-user, known for starring in 'brainrot battle' videos against other characters.",
    },
    {
        "name": "Cappuccino Assassino",
        "visual": "an espresso cup with cartoon arms and legs dressed as a ninja, dramatic action pose, dark moody lighting, photorealistic 3D render",
        "lore": "A ninja-dressed espresso cup -- often paired with Ballerina Cappuccina in dramatic storylines, especially popular for its wordplay in Portuguese and Spanish.",
    },
    {
        "name": "La Vacca Saturno Saturnita",
        "visual": "a cow with the rings of the planet Saturn orbiting around its body, floating in space, cinematic lighting, photorealistic 3D render",
        "lore": "A cow with Saturn's rings orbiting its body -- known for appearing in slow-motion, cinematic-style edits that give the genre a grander, cosmic tone.",
    },
    {
        "name": "Bommodini Gusini",
        "visual": "a goose riding on top of a large bomb like a rocket, comedic pose, plain background, photorealistic 3D render",
        "lore": "A goose riding a bomb -- the genre's foolish sidekick character, usually cast as comic relief alongside more serious characters.",
    },
    {
        "name": "Frigo Camelo",
        "visual": "a camel whose body is also a refrigerator, with a visible fridge door and handle on its side, standing, plain background, photorealistic 3D render",
        "lore": "A camel that's also a refrigerator -- beloved for its distinctive, lullaby-like audio loop that other creators layer under their own clips.",
    },
    {
        "name": "Tric Trac Baraboom",
        "visual": "a drum kit with cartoon arms and legs, mid-drumming pose, stage lighting, photorealistic 3D render",
        "lore": "A drum kit with arms and legs -- the genre's percussion character, increasingly used in videos where the visuals sync to a musical beat.",
    },
]
