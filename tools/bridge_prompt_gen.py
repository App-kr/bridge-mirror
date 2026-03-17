#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRIDGE 4K Reality Prompt Generator  v2.0
~2000-rule combinatorial engine — no API required

Usage:
  python bridge_prompt_gen.py                   # random 5 prompts
  python bridge_prompt_gen.py -n 10             # 10 prompts
  python bridge_prompt_gen.py -t early          # early childhood only
  python bridge_prompt_gen.py -t middle         # middle/high school only
  python bridge_prompt_gen.py -o out.txt        # save to file
  python bridge_prompt_gen.py --stats           # show rule counts
"""

import random
import argparse
import sys
from datetime import datetime

# =============================================================================
# RULE BANK
# Each list is an independent dimension.  A prompt is built by picking one
# item (or a few) from each relevant dimension and assembling them.
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# DIM-01  FLOOR MATERIALS  (40 items)
# ─────────────────────────────────────────────────────────────────────────────
FLOORS = [
    "polished hardwood parquet flooring with warm honey tones",
    "matte light-oak engineered wood panels",
    "glossy white ceramic tile flooring",
    "soft pastel-blue foam mat flooring",
    "colorful interlocking EVA foam tiles in primary colors",
    "speckled linoleum flooring in warm beige",
    "smooth poured concrete with a subtle sheen",
    "herringbone-patterned pale oak hardwood",
    "non-slip rubber athletic flooring in charcoal gray",
    "sprung maple hardwood sports floor",
    "cobblestone-patterned decorative tile (indoor themed area)",
    "soft carpet in warm grey with alphabet border stitching",
    "large-format porcelain tiles in light cream",
    "warm terracotta-toned ceramic tile",
    "bamboo flooring panels in natural green-tan hue",
    "industrial epoxy resin floor in cool gray",
    "bright yellow-and-blue checkerboard vinyl flooring",
    "cushioned play floor with star and circle motif",
    "fine-grain neutral concrete with sealer finish",
    "warm walnut hardwood with a satin finish",
    "anti-fatigue foam matting in forest green",
    "deep charcoal rubber flooring with yellow lane markers",
    "pale birch laminate flooring with micro-bevel edges",
    "smooth resin terrazzo in white and pale gold",
    "soft grey felt carpet tiles arranged in a grid",
    "light maple strip flooring with a gymnasium sheen",
    "bold rainbow-segment activity floor for children",
    "cool slate-grey anti-static lab flooring",
    "warm sienna-stained concrete microcement",
    "pastel mint green vinyl roll flooring",
    "brushed stainless-steel stage floor panels",
    "dance studio sprung floor with light beech finish",
    "translucent tempered glass floor panels with LED underlighting",
    "woven jute area rug over light hardwood",
    "climbing-wall padded crash-mat flooring in blue",
    "large pale terrazzo tiles with grey aggregate",
    "natural stone-look porcelain slabs in warm ivory",
    "recycled rubber flooring with subtle circular texture",
    "semi-gloss cream epoxy lab floor with anti-slip grit",
    "bold red-and-white striped activity floor for gym warm-up zone",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-02  WALL TREATMENTS  (50 items)
# ─────────────────────────────────────────────────────────────────────────────
WALLS = [
    "walls painted in warm white with subtle texture",
    "exposed brick wall painted matte white",
    "raw exposed brick in natural terracotta tones",
    "floor-to-ceiling glass curtain wall overlooking a green campus",
    "acoustic foam panels in charcoal arranged in a grid",
    "colorful phonics alphabet posters covering one wall",
    "world map mural spanning the entire back wall",
    "chalkboard-painted feature wall covered in student notes",
    "whiteboard wall with colorful dry-erase writing",
    "warm wood slat paneling running horizontally",
    "deep navy blue accent wall with star constellation decals",
    "pale sage green painted walls with white trim",
    "full-length mirror wall reflecting the entire room",
    "concrete block wall with industrial grey finish",
    "pastel yellow walls with cartoon English-learning stickers",
    "glass-walled partition dividing lab zones",
    "corrugated metal cladding painted in muted grey-blue",
    "light-grey textured plaster walls with shadow gaps",
    "colorful murals of world cities and landmarks",
    "panoramic window looking out to a tree-lined courtyard",
    "bright coral-orange feature wall behind the teacher's station",
    "vertical garden wall with real climbing plants",
    "linen-textured cream wallpaper with geometric pattern",
    "frosted glass partition with abstract etched design",
    "soft periwinkle blue walls with floating wooden shelves",
    "library-style bookshelves built into both side walls",
    "tall pegboard wall holding craft supplies in labeled bins",
    "theatrical black curtain backdrop wall with track lighting",
    "sky blue walls with clouds mural for early learners",
    "warm sand-colored stucco wall with recessed LED niches",
    "high-gloss white walls with color-band wayfinding stripes",
    "scientific periodic table wall print from floor to ceiling",
    "motivational English quotes typography wall in black and gold",
    "reclaimed wood shiplap paneling in weathered grey",
    "vibrant cartoon English village scene mural",
    "dark charcoal walls with neon accent lines — e-sports lab style",
    "pastel pink walls with framed children's artwork gallery",
    "exposed structural steel columns against off-white plaster",
    "holographic interactive display wall (themed center)",
    "pale turquoise walls with white wave-form acoustic baffles",
    "heritage brick restored with clear protective sealer",
    "deep forest-green walls with gold leaf framed learning charts",
    "soft lilac walls with floating white cloud sculptures",
    "warm amber-lit wood-panel walls in library reading room",
    "bold color-blocked walls — yellow left panel, white right",
    "transparent polycarbonate panels revealing structural beams",
    "iridescent tile mosaic accent wall behind the whiteboard",
    "concrete wall with large-format school crest relief",
    "mint green walls with educational number-line border frieze",
    "soft-grey noise-reducing fabric wall panels with stitched pattern",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-03  CEILING DETAILS  (30 items)
# ─────────────────────────────────────────────────────────────────────────────
CEILINGS = [
    "exposed industrial ductwork and concrete soffit painted white",
    "dropped acoustic tile ceiling with recessed LED panels",
    "high vaulted ceiling with exposed timber trusses",
    "skylights flooding the room with natural daylight",
    "colorful paper lantern installations hanging from above",
    "strings of warm Edison bulb fairy lights criss-crossing overhead",
    "double-height glass atrium ceiling with steel grid",
    "stage rigging grid with adjustable spotlights",
    "painted sky blue ceiling with cloud motifs",
    "suspended cloud-shaped acoustic baffles in white",
    "mirrored ceiling panel adding depth over the performance space",
    "coffered ceiling in cream with subtle gold molding",
    "raw concrete ceiling with black industrial track lighting",
    "translucent polycarbonate roof diffusing soft daylight",
    "low suspended ceiling with colorful hexagonal tiles",
    "dome-shaped ceiling with star-field projection",
    "cathedral ceiling with dramatic arched wooden beams",
    "flat white ceiling with minimalist recessed downlights",
    "hanging mobile artwork installation of English alphabet letters",
    "LED strip lighting in warm white tracing the ceiling perimeter",
    "undulating wave-form white acoustic ceiling panels",
    "hanging origami bird installation above the reading circle",
    "black box theatre ceiling — all black, grid of fresnels",
    "bamboo slat ceiling panels creating organic rhythm",
    "glass clerestory windows high on walls letting in sidelight",
    "colorful kite-shaped fabric canopies suspended from ceiling",
    "large rectangular HVAC grilles integrated into white ceiling",
    "metallic silver sound diffuser panels arranged geometrically",
    "warm wooden tongue-and-groove ceiling with pendant lamps",
    "concrete ceiling with embedded round LED dot matrix pattern",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-04  AMBIENT LIGHTING QUALITIES  (50 items)
# ─────────────────────────────────────────────────────────────────────────────
LIGHTING_AMBIENT = [
    "golden morning light streaming through east-facing windows",
    "soft diffused afternoon daylight filling the space evenly",
    "warm 3200K tungsten interior lighting",
    "neutral 4000K cool-white LED panels",
    "warm 2700K vintage Edison bulb warmth",
    "bright 6500K daylight-balanced studio lighting",
    "overcast sky producing flat even shadowless outdoor light",
    "dramatic low-key side lighting with deep shadows",
    "high-key bright even illumination eliminating harsh shadows",
    "split lighting — half face lit, half in shadow, dynamic contrast",
    "soft window light from a north-facing window, even and cool",
    "theatrical Fresnel spot creating a strong key light on subject",
    "colorful RGB stage wash in complementary hues",
    "neon accent lighting in cyan and magenta tones",
    "warm pendant lamps creating pools of intimate light",
    "cool fluorescent overhead lighting of a science lab",
    "backlit window creating a gentle rim light on the instructor",
    "amber-toned late afternoon 'golden hour' light",
    "blue-tinted dusk light through large windows",
    "mixed daylight and warm incandescent — natural color contrast",
    "large softbox equivalent — oversized window acting as fill",
    "fairy lights creating a warm twinkling ambient background",
    "skylight overhead producing a natural fill with soft shadows",
    "spotlit single beam on whiteboard area, room in shadow",
    "soft ring-light frontal fill creating catchlights in eyes",
    "moody Rembrandt-style single side key light",
    "twin key-fill balanced studio setup",
    "classroom fluorescent tubes with slight flicker warmth",
    "recessed downlights creating scalloped wall wash",
    "track lighting accenting specific activity zones",
    "morning haze diffusing through sheer curtains",
    "crisp winter daylight — high contrast cool tones",
    "warm spring afternoon light through open curtains",
    "bright summer noon light bleaching color slightly",
    "deep autumn amber slant light through blinds creating stripes",
    "softbox-equivalent overcast sky for outdoor scenes",
    "underwater-tinted teal light for science lab scene",
    "dramatic cove lighting bounced off high ceiling",
    "LED panel overhead filling evenly — clinical bright",
    "canopy-filtered dappled natural light for outdoor courtyard",
    "wall-washer LED creating gradient on feature wall",
    "uplighting from floor fixtures accenting architectural columns",
    "colored gel wash — warm amber on instructor, cool blue on BG",
    "side-window light — strong directional, long shadows on floor",
    "stage follow-spot isolating instructor from dim background",
    "soft bounce light from white reflector card on fill side",
    "diffused light through translucent ceiling panels, even overall",
    "reading lamp individual pools of warm light",
    "stadium-style overhead floodlights — sports hall",
    "mixed: cool daylight from windows + warm tungsten accent",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-05  INSTRUCTOR RACE + GENDER  (18 combos)
# ─────────────────────────────────────────────────────────────────────────────
INSTRUCTOR_RG = [
    ("White", "male"),
    ("White", "female"),
    ("Black", "male"),
    ("Black", "female"),
    ("Latino", "male"),
    ("Latina", "female"),
    ("South Asian", "male"),
    ("South Asian", "female"),
    ("East Asian", "male"),
    ("East Asian", "female"),
    ("Middle Eastern", "male"),
    ("Middle Eastern", "female"),
    ("Southeast Asian", "male"),
    ("Southeast Asian", "female"),
    ("Mixed-race", "male"),
    ("Mixed-race", "female"),
    ("Native American", "male"),
    ("Pacific Islander", "female"),
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-06  INSTRUCTOR HAIR STYLES  (50 items)
# ─────────────────────────────────────────────────────────────────────────────
HAIR = [
    "short neat side-part",
    "close-cropped natural afro",
    "long straight dark hair worn loose",
    "shoulder-length wavy auburn hair",
    "tight coiled natural hair in a high bun",
    "braided cornrows styled back neatly",
    "thick black hair in a sleek ponytail",
    "medium-length curly brown hair",
    "shaved head with faded sides",
    "silver-streaked short professional cut",
    "long flowing locs gathered over one shoulder",
    "pixie cut in natural black",
    "undercut with wavy top styled back",
    "bob cut in rich espresso brown",
    "short textured crop with slight fade",
    "long beachy waves in caramel blonde",
    "buzz cut revealing natural head shape",
    "double buns — playful style for early childhood setting",
    "French braid crown for a polished look",
    "loose chignon low bun at nape",
    "thick silver natural locs — distinguished look",
    "curly red hair medium length",
    "straight black hair with blunt bangs",
    "long box braids worn down",
    "tightly twisted natural hair mid-length",
    "short grey tapered cut",
    "swept-back pompadour in dark brown",
    "half-up half-down with natural curls",
    "deep side-swept waves past shoulders",
    "dreadlocks gathered in a loose ponytail",
    "short afro with a fade",
    "long straight platinum blonde hair",
    "kinky coils in a defined puff",
    "layered chestnut hair just below chin",
    "cropped textured natural hair — salt and pepper",
    "loose romantic updo with face-framing tendrils",
    "slick back gel style — professional and sharp",
    "voluminous curly medium-length in warm brown",
    "short graduated bob in jet black",
    "long loosely braided plait over shoulder",
    "short choppy pixie with side-swept fringe",
    "medium-length natural twist-out style",
    "waist-length straight dark hair",
    "tousled messy bun — casual professional",
    "structured quiff in sandy brown",
    "tapered natural hair with defined coils",
    "loose waves in warm honey tones",
    "asymmetric short cut — bold and modern",
    "mid-length balayage in dark root to caramel ends",
    "very short natural hair with warm undertone skin",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-07  INSTRUCTOR UPPER CLOTHING  (60 items)
# ─────────────────────────────────────────────────────────────────────────────
UPPER_CLOTHING = [
    "fitted navy blazer over a crisp white dress shirt",
    "colorful patterned blouse in coral and white",
    "casual pale blue Oxford shirt, top button open",
    "soft heather-grey V-neck sweater",
    "professional charcoal suit jacket",
    "bright yellow cardigan over a white undershirt",
    "smart olive-green bomber jacket",
    "striped Breton top in navy and white",
    "fitted turtleneck in warm burgundy",
    "lightweight denim jacket over floral blouse",
    "athletic tracksuit jacket in royal blue with white stripes",
    "crisp pressed white lab coat",
    "earthy terracotta linen button-down shirt",
    "slim-cut black turtleneck — minimalist style",
    "pastel pink oversized blazer",
    "forest green utility overshirt",
    "classic white polo shirt",
    "merino wool crew-neck sweater in camel",
    "bold geometric print short-sleeve shirt",
    "soft lavender quarter-zip pullover",
    "well-fitted dark denim shirt",
    "colourblock zip-up hoodie in teal and grey",
    "silk blouse in deep sapphire blue",
    "light grey marl sweatshirt — relaxed fit",
    "sleeveless mandarin-collar blouse in ivory",
    "smart casual checked flannel shirt in earth tones",
    "technical sports jersey — international school PE",
    "tailored black mock-neck top",
    "bright red crewneck sweater",
    "sheer white blouse over camisole",
    "structured plum-colored blazer",
    "striped linen button-down in soft peach",
    "oversized cream knit cardigan with pockets",
    "slim-fit cobalt blue dress shirt",
    "patterned ethnic-print dashiki top",
    "sporty performance polo in charcoal",
    "lightweight khaki utility shirt",
    "colorful embroidered kurta top",
    "mock-neck fitted ribbed top in olive",
    "classic teacher cardigan in soft mustard",
    "business-casual white blouse with bow tie collar",
    "athletic long-sleeve base layer in slate blue",
    "corduroy overshirt in warm rust",
    "paint-stained smock over a neutral top (art class)",
    "short-sleeve linen shirt in washed indigo",
    "bold abstract-print blouse in warm tones",
    "sleek black button-through dress shirt",
    "cozy chunky knit pullover in oatmeal",
    "slim cashmere V-neck in forest green",
    "soft cotton jersey top in dusty rose",
    "technical moisture-wicking polo for gym instructor",
    "crisply ironed school-crest polo in white",
    "lightweight chambray shirt in soft blue",
    "printed batik short-sleeve top",
    "smart dark navy sweatshirt with minimalist logo",
    "formal waistcoat over light dress shirt",
    "cropped blazer in warm tan over high-waist trousers",
    "relaxed fit flannel in charcoal plaid",
    "vibrant orange knit top — stands out against neutral BG",
    "monochrome black athletic long-sleeve tee",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-08  INSTRUCTOR POSE / GESTURE  (60 items)
# ─────────────────────────────────────────────────────────────────────────────
POSES = [
    "gesturing enthusiastically toward a whiteboard",
    "kneeling at a child's eye level with a warm smile",
    "standing with arms open in an inviting gesture",
    "holding up a large colorful flashcard",
    "sitting cross-legged on the floor with students gathered around",
    "pointing to something on an interactive smartboard",
    "clapping hands to the rhythm of a song",
    "reading aloud from an oversized picture book",
    "crouching next to a student to guide their work",
    "writing on a whiteboard mid-sentence, marker in hand",
    "arms crossed confidently, scanning the room",
    "leaning forward on a desk, engaged in student conversation",
    "making a two-hand 'frame' gesture while explaining",
    "mid-step walking between student desks",
    "holding a globe and pointing to a location",
    "giving a thumbs-up to a student who answered correctly",
    "conducting students with both hands like an orchestra",
    "holding a marker and pausing mid-thought",
    "demonstrating a science procedure with both hands",
    "high-fiving a student in an encouraging moment",
    "gesturing to two students to collaborate",
    "leaning back against the teacher's desk, relaxed and engaged",
    "standing tall at the front of the room, confident posture",
    "holding a clipboard and reviewing student work",
    "extending one hand palm-up in an explanatory gesture",
    "demonstrating a dance move with arms extended",
    "strumming or pointing to a musical instrument",
    "blowing a whistle with one arm pointing direction — PE",
    "adjusting a student's art piece with gentle hands",
    "turning to face the room while writing, mid-sentence",
    "using both hands to count off points on fingers",
    "bending over a lab bench to show a technique",
    "stepping forward to make eye contact with a student",
    "spreading both arms wide in an expressive storytelling pose",
    "placing a hand on a student's shoulder encouragingly",
    "snapping fingers to get the class's attention",
    "pointing upward as if referencing a key concept",
    "sitting on the edge of a desk casually addressing the group",
    "making a circle gesture with both hands — 'gather around' pose",
    "walking and gesturing simultaneously — dynamic motion blur",
    "holding a book open to a page and showing it to camera",
    "mid-clap celebrating a student achievement",
    "pointing to a student who raised their hand",
    "facing slightly away, shoulder toward camera, dynamic profile",
    "reaching up to a high shelf for a teaching prop",
    "holding chalk in one hand, turning from chalkboard",
    "demonstrating proper form — hand on chin, thinking pose",
    "handing out worksheets while smiling at students",
    "kneeling beside a student's wheelchair or low seat",
    "tossing a soft foam ball to a participating student",
    "pointing to a large printed infographic on the wall",
    "making an 'OK' sign and nodding in affirmation",
    "sweeping one arm across the room in introduction gesture",
    "using sign language alongside spoken words",
    "mid-laugh sharing a moment of humor with students",
    "squatting beside a small group working on the floor",
    "standing in strong pose facing three-quarter to camera",
    "holding a tablet showing content to nearby student",
    "raising one eyebrow and tilting head — Socratic questioning pose",
    "using a laser pointer on a projected map or diagram",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-09  INSTRUCTOR FACIAL EXPRESSION  (30 items)
# ─────────────────────────────────────────────────────────────────────────────
EXPRESSIONS = [
    "warm encouraging smile with kind eyes",
    "animated and excited expression",
    "calm and focused, thoughtful gaze",
    "mid-laugh, genuinely joyful",
    "raised eyebrow in a playful challenge",
    "proud and affirming smile",
    "intense concentration, brows slightly furrowed",
    "wide-eyed wonder matching the children's excitement",
    "composed, professional, and attentive",
    "gentle and patient expression",
    "bright enthusiastic grin, teeth showing",
    "soft smile with a knowing, experienced look",
    "curious, tilting head slightly to one side",
    "firm but kind — authoritative without coldness",
    "expression of delight discovering something with students",
    "relaxed and open, approachable demeanor",
    "mildly theatrical expression for storytelling",
    "deep listening expression — nodding, leaning in slightly",
    "encouraging nod with a half-smile",
    "pensive — pausing before a key reveal moment",
    "bright eyes and a subtle smirk — witty and engaging",
    "serene and confident — a natural classroom leader",
    "energetic and upbeat, eyebrows raised",
    "empathetic expression — listening to a student's question",
    "proud instructor beam — watching a student succeed",
    "slight squint of concentration reviewing student work",
    "open mouth mid-sentence explaining passionately",
    "laughing softly with eyes closed — genuine moment",
    "attentive and direct — making strong eye contact with camera",
    "warm half-smile, slightly turned head — candid portrait feel",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-10  INSTRUCTOR AGE DESCRIPTORS  (15 items)
# ─────────────────────────────────────────────────────────────────────────────
AGES = [
    "appearing to be in their mid-20s — early career teacher",
    "appearing to be in their early 30s — confident and experienced",
    "appearing to be in their mid-30s — seasoned professional",
    "appearing to be in their late 30s — expert educator",
    "appearing to be in their early 40s — master teacher",
    "appearing to be in their mid-40s — experienced and composed",
    "appearing to be in their early 50s — distinguished educator",
    "appearing to be in their late 20s — energetic and fresh",
    "appearing to be in their 30s — peak career energy",
    "appearing to be in their 40s — authoritative yet approachable",
    "appearing to be in their 50s — mentor figure",
    "a youthful-looking instructor in their late 20s",
    "a warm middle-aged educator in their 40s",
    "a lively young instructor barely out of university",
    "a mature and distinguished instructor in their 50s",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-11  EARLY CHILDHOOD PLACE TYPES  (25 items)
# ─────────────────────────────────────────────────────────────────────────────
PLACES_EARLY = [
    {
        "name": "Colorful English Kindergarten Classroom",
        "desc": "bright pastel-colored Korean English kindergarten classroom with low round tables, alphabet posters, colorful chairs sized for young children, picture books on low shelves",
        "mood": "warm, playful, and nurturing",
    },
    {
        "name": "English Play Room (영어 유치원)",
        "desc": "cheerful English play-learning room with soft foam flooring in primary colors, interactive phonics wall panels, a pretend-play corner with costumes, stuffed animals and English-labeled props",
        "mood": "imaginative, joyful, and immersive",
    },
    {
        "name": "Outdoor Playground Learning Area",
        "desc": "modern preschool outdoor learning area with bright artificial turf, colorful wooden playground structures, nature exploration stations, low garden beds",
        "mood": "energetic, natural, and exploratory",
    },
    {
        "name": "Story Circle Room",
        "desc": "cozy story-time circle area with semicircular cushioned seating on a soft rug, a large interactive smartboard showing English storybook illustrations, plush animal characters on display shelves",
        "mood": "magical, attentive, and wonder-filled",
    },
    {
        "name": "Art & Craft Learning Room",
        "desc": "bright art and craft room with child-height tables covered in colorful materials, walls lined with children's finished artwork, paint supply stations, drying racks with paper crafts",
        "mood": "creative, expressive, and joyful",
    },
    {
        "name": "English Village Town Square (영어마을)",
        "desc": "indoor themed English village modeled as a colorful Western small town, miniature storefronts — bakery, post office, toy shop — cobblestone-patterned floor tiles, decorative street lamps, English signage everywhere",
        "mood": "magical, immersive, and adventurous",
    },
    {
        "name": "English Village Airport Zone",
        "desc": "realistic mock airport terminal inside a Korean English experience center, check-in counters with English signage, prop luggage conveyor, departure board showing English city names, customs desk with passport props",
        "mood": "exciting, functional, and role-play immersive",
    },
    {
        "name": "English Experience Center Restaurant Zone",
        "desc": "themed mock restaurant inside a Korean English immersion center, diner-style booths and counter stools, chalkboard menu in English, plastic food props, wait-staff uniforms for children",
        "mood": "fun, interactive, and communicative",
    },
    {
        "name": "English Learning Center Classroom (영어 학원)",
        "desc": "modern Korean English language center classroom, wall-to-wall English phonics charts and world maps, tiered seating with individual whiteboards, interactive smartboard with animated lessons",
        "mood": "structured, energetic, and motivating",
    },
    {
        "name": "English Village Hospital Zone",
        "desc": "realistic mock hospital ward inside a Korean English village center, examination beds with curtain dividers, doctor's desk with English medical charts, nurse station, medical equipment props",
        "mood": "focused, role-play immersive, and educational",
    },
    {
        "name": "English Library Reading Zone",
        "desc": "cozy English picture book library inside a Korean early learning center, floor-to-ceiling shelves of colorful English books, bean bag chairs and reading nooks, alphabet-border story-time rug",
        "mood": "calm, curious, and imagination-sparking",
    },
    {
        "name": "English Village Science Exploration Zone",
        "desc": "interactive science zone inside a Korean English experience center, hands-on experiment stations labeled in English, volcano model, simple circuit boards, plant growth experiments, science murals",
        "mood": "curious, discovery-driven, and bilingual",
    },
    {
        "name": "English Village Supermarket Zone",
        "desc": "themed indoor mini supermarket, color-coded aisles with English-labeled product categories, shopping baskets and carts sized for children, mock cashier station with conveyor belt prop",
        "mood": "practical, communicative, and fun",
    },
    {
        "name": "English Village Fire Station Zone",
        "desc": "miniature fire station themed room, fire truck prop vehicle, English-labeled safety equipment display, firefighter uniforms for children, safety-information posters in English",
        "mood": "exciting, role-play, and safety-conscious",
    },
    {
        "name": "English Village Post Office Zone",
        "desc": "miniature post office with service counter, English address labels, prop postboxes, parcel-packaging table, postal worker uniforms for children, sorting station",
        "mood": "structured, communicative, and charming",
    },
    {
        "name": "Sensory Play English Room",
        "desc": "soft-play sensory exploration room with English-labeled tactile panels, sand and water tables with bilingual instructions, bubble walls, mirror maze section",
        "mood": "exploratory, sensory-rich, and bilingual",
    },
    {
        "name": "English Phonics Music Room",
        "desc": "small music and phonics room with colorful percussion instruments, rhythm carpet, English song posters, a piano keyboard along one wall, acoustic ceiling tiles",
        "mood": "rhythmic, joyful, and phonics-focused",
    },
    {
        "name": "English Drama Mini-Stage",
        "desc": "small performance stage built inside an English kindergarten, mini stage risers, colorful curtain, prop costume rack, audience seating of low cushions for classmates",
        "mood": "performative, creative, and confidence-building",
    },
    {
        "name": "Nature Discovery English Garden",
        "desc": "rooftop or ground-level school garden with labeled planters in English, butterfly observation dome, weather station, outdoor classroom seating, clear sky above",
        "mood": "natural, scientific, and bilingual",
    },
    {
        "name": "English Cooking Studio (어린이 요리실)",
        "desc": "child-height cooking studio with low countertops, English-labeled ingredient jars, aprons sized for children, sample recipe posters in English, safe induction cooktops",
        "mood": "hands-on, sensory, and language-rich",
    },
    {
        "name": "English Block Building Room",
        "desc": "open play room with giant foam building blocks in primary colors, English-labeled construction challenge cards on display, low bins of colored materials, open floor space",
        "mood": "creative, spatial, and energetic",
    },
    {
        "name": "Morning Circle English Classroom",
        "desc": "early morning assembly-style classroom, day-of-week and weather chart on the wall, attendance board with student photo cards, calendar in English, bright motivational banner",
        "mood": "warm, routine-positive, and structured",
    },
    {
        "name": "English STEAM Discovery Lab (유아)",
        "desc": "early childhood STEAM lab with age-appropriate robotics toys, magnetic tile sets, coding puzzles with English instructions, bright display of student creations",
        "mood": "innovative, hands-on, and language-forward",
    },
    {
        "name": "English Immersion Camp Cabin Room",
        "desc": "English immersion camp-style cabin room with bunk-bed style cubbies, each with a flag and English name card, group activity tables, camp-theme murals, outdoor light filtering in",
        "mood": "adventurous, community-focused, and bilingual",
    },
    {
        "name": "English Village Bank and Currency Zone",
        "desc": "themed mini bank inside an English experience center, teller windows with English signage, prop currency and banking forms, vault door prop, learning about transactions in English",
        "mood": "educational, transactional-play, and real-world",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-12  MIDDLE / HIGH SCHOOL PLACE TYPES  (25 items)
# ─────────────────────────────────────────────────────────────────────────────
PLACES_MIDDLE = [
    {
        "name": "International School Gymnasium",
        "desc": "modern international school indoor gymnasium with polished hardwood floors, basketball court markings, athletic equipment racks, tall clerestory windows",
        "mood": "energetic and competitive",
    },
    {
        "name": "International School Music Rehearsal Room",
        "desc": "intimate acoustic rehearsal room, sound-absorbing wall panels, diverse instruments — drums, keyboard, violins — music stands with sheet music",
        "mood": "creative and focused",
    },
    {
        "name": "International School Auditorium Stage",
        "desc": "large performance stage with dramatic spotlights, professional lighting towers, theatrical set pieces, dark auditorium seating in background",
        "mood": "dramatic and inspiring",
    },
    {
        "name": "IB Curriculum Modern Classroom",
        "desc": "bright contemporary IB classroom with modular movable desks, large interactive whiteboard, student tablets, world-map graphics, floor-to-ceiling windows overlooking a green campus",
        "mood": "intellectually engaged and collaborative",
    },
    {
        "name": "International School Science Laboratory",
        "desc": "cutting-edge high school science lab, glass-partitioned research spaces, microscopes, colorful glassware and flasks, safety equipment stations, periodic table mural",
        "mood": "precise and investigative",
    },
    {
        "name": "Korean International School Study Hall",
        "desc": "quiet study hall combining independent study booth style, individual desk lamps, stacked reference books, clean minimal aesthetic, motivational quotes on the wall",
        "mood": "contemplative, determined, and aspirational",
    },
    {
        "name": "International School Dance Practice Room",
        "desc": "professional dance practice room, full-length mirrored walls, ballet barre along one side, sprung hardwood floor, scattered dance props",
        "mood": "dynamic, disciplined, and artistic",
    },
    {
        "name": "International School Makerspace",
        "desc": "creative makerspace with 3D printers, laser cutters behind safety glass, electronics workbenches, soldering stations, colorful project materials, industrial pipe shelving",
        "mood": "innovative, hands-on, and collaborative",
    },
    {
        "name": "International School Debate Classroom",
        "desc": "specialized debate classroom with circular table arrangement, presentation screens, a podium at front, subtle acoustic paneling, professional conference atmosphere",
        "mood": "intellectual, assertive, and articulate",
    },
    {
        "name": "International School Art Studio",
        "desc": "spacious high school art studio, easels with student work-in-progress, wall of completed paintings, art supply trolleys, north-facing skylight providing ideal diffused light",
        "mood": "expressive, free, and artistic",
    },
    {
        "name": "International School Computer Lab",
        "desc": "modern computer science lab, dual-monitor workstations, visible server racks behind glass, students coding, soft blue underglow from screens in a dark room",
        "mood": "focused, technical, and future-oriented",
    },
    {
        "name": "International School Library",
        "desc": "modern school library with high shelves of books, comfortable reading chairs, globe displays, study pods with privacy screens, warm wood tones and soft lighting",
        "mood": "quiet, curious, and intellectually rich",
    },
    {
        "name": "International School Swimming Pool Area",
        "desc": "indoor Olympic-standard swimming pool, lane markers, starting blocks, viewing gallery, high ceiling with ventilation, aqua water reflections on walls",
        "mood": "athletic, disciplined, and focused",
    },
    {
        "name": "International School Cafeteria / Commons",
        "desc": "bright modern school cafeteria with long communal tables, natural light from full-wall windows, international food station signage, student artwork on walls",
        "mood": "social, vibrant, and multicultural",
    },
    {
        "name": "International School Outdoor Sports Field",
        "desc": "international school FIFA-regulation artificial turf football field, surrounding track, stadium flood lights, clear sky, goal posts visible, students in team jerseys",
        "mood": "competitive, healthy, and team-spirited",
    },
    {
        "name": "International School Photography Darkroom",
        "desc": "traditional photography darkroom, red safelight glow, developing trays, enlargers, prints drying on wire lines, a rare and atmospheric teaching space",
        "mood": "atmospheric, artistic, and technical",
    },
    {
        "name": "International School Robotics Lab",
        "desc": "dedicated robotics classroom, competition-spec robots on tables, coding stations, arena floor for robot testing, trophies from previous competitions displayed",
        "mood": "innovative, competitive, and team-driven",
    },
    {
        "name": "International School Ceramics Studio",
        "desc": "hands-on ceramics studio, potter's wheels, shelves of drying clay forms, kiln area, earthy textures and materials, clay-dusted surfaces, natural light from high windows",
        "mood": "tactile, patient, and artistic",
    },
    {
        "name": "International School Video Production Suite",
        "desc": "professional-grade school video production room, green screen backdrop, camera rigs, editing workstations with dual monitors, broadcast-quality lighting equipment",
        "mood": "creative, technical, and media-forward",
    },
    {
        "name": "International School Student Lounge",
        "desc": "modern student common area, colorful modular seating, collaborative work tables, large screens showing school news, vending machines, energetic social hub",
        "mood": "social, relaxed, and multicultural",
    },
    {
        "name": "International School Yoga and Mindfulness Room",
        "desc": "serene yoga and mindfulness studio, bamboo mats rolled out, calming neutral tones, a single feature wall with nature mural, plants, diffuse soft lighting",
        "mood": "calm, focused, and wellness-oriented",
    },
    {
        "name": "International School Orchestra Rehearsal Hall",
        "desc": "full-size orchestra rehearsal hall with tiered risers, music stands for 40+ musicians, conductor's podium, acoustic shell panels, instrument storage cabinets",
        "mood": "disciplined, collaborative, and majestic",
    },
    {
        "name": "International School ESL Conversation Room",
        "desc": "small-group English conversation room, round table for 6 students, vocabulary cards on walls, a language lab headset station along one wall, friendly learning atmosphere",
        "mood": "warm, conversational, and confidence-building",
    },
    {
        "name": "International School Innovation Hub",
        "desc": "open-plan innovation and design thinking space, movable whiteboards, mood boards, prototype materials, standing-height tables, natural light from skylights",
        "mood": "creative, entrepreneurial, and collaborative",
    },
    {
        "name": "International School Nursing Room / Health Suite",
        "desc": "bright modern school health suite, examination beds behind privacy curtains, health posters in English and Korean, medical supplies cabinet, welcoming reception area",
        "mood": "caring, calm, and safe",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-13  STUDENT GROUP COMPOSITION  (40 items — early)
# ─────────────────────────────────────────────────────────────────────────────
STUDENTS_EARLY = [
    "5 Korean preschoolers (ages 3-5) sitting cross-legged on the floor, clapping to an English song",
    "6 mixed Korean and multicultural kindergartners (ages 4-6) gathered in a semicircle on colorful cushions",
    "7 Korean children (ages 5-7) at low tables, focused on an English worksheet activity",
    "5 preschool children in matching school uniforms (ages 4-5), lined up and smiling at the teacher",
    "6 diverse kindergartners including Korean and mixed-race children (ages 4-6) playing role-play English scenarios",
    "8 young Korean students (ages 6-8) standing in a line practicing English phonics chants",
    "4 Korean children (ages 5-6) and 2 mixed-race children huddled around a single large English picture book",
    "6 Korean toddlers (ages 3-4) waving colorful English flashcards in the air with excitement",
    "5 Korean early learners (ages 6-7) taking turns performing an English skit for classmates",
    "7 multicultural early childhood students including Korean children, making English letter crafts at tables",
    "4 Korean children (ages 5-6) in small group with one child standing confidently saying English words",
    "6 Korean preschoolers in activity aprons doing an English cooking vocabulary lesson",
    "5 diverse kindergartners including 3 Korean students pointing to a world map together",
    "8 Korean children (ages 6-7) laughing and participating in a team English game",
    "6 young Korean and multicultural students practicing English greetings with gestures",
    "5 Korean children (ages 4-5) each holding up a letter card, spelling out E-N-G-L-I-S-H",
    "7 Korean early learners (ages 6-8) racing to put English word-picture pairs together",
    "4 Korean preschoolers listening attentively while one child stands up to speak in English",
    "6 diverse Korean and expat children (ages 5-7) at an outdoor station examining nature with English labels",
    "8 energetic Korean kindergartners (ages 5-6) jumping up answering English questions enthusiastically",
    "5 Korean children (ages 6-8) at English drama mini-stage, one in costume performing proudly",
    "6 Korean young students with colorful English storybooks, each reading a page aloud in turn",
    "4 Korean toddlers (ages 3-4) using giant foam puzzle letters together on the floor",
    "7 Korean mixed-age early learners (ages 5-8) in a circle passing an 'English talking stick'",
    "5 Korean and multicultural students (ages 6-7) in front of an English village storefront prop",
    "6 Korean preschoolers proudly holding up their finished English alphabet collage artwork",
    "8 diverse young students (ages 4-6) participating in a bilingual English-Korean call-and-response game",
    "4 Korean children (ages 5-7) at individual tablet stations completing English phonics exercises",
    "7 Korean kindergartners in chef hats doing an English cooking vocabulary role-play",
    "6 Korean early learners (ages 6-8) paired up, one asking and one answering English questions",
    "5 Korean and mixed-race preschoolers building with giant blocks labeled with English words",
    "8 Korean children (ages 5-7) raising hands high — every single child eager to answer in English",
    "4 Korean students (ages 6-8) at the role-play airport check-in desk speaking English with the teacher",
    "6 diverse preschool children including Korean students at the English science experiment table",
    "7 Korean young learners (ages 5-6) wearing doctor costumes in the English hospital zone",
    "5 Korean children (ages 6-8) and one mixed-race child reading quietly in the English book nook",
    "8 Korean kindergartners (ages 4-6) doing TPR (Total Physical Response) actions for English verbs",
    "4 Korean preschool children (ages 3-5) singing an English counting song with hand gestures",
    "6 Korean early learners at a sensory water table, using English vocabulary cards for objects",
    "5 multicultural early childhood students doing fingerpainting while a teacher narrates in English",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-14  STUDENT GROUP COMPOSITION  (40 items — middle/high)
# ─────────────────────────────────────────────────────────────────────────────
STUDENTS_MIDDLE = [
    "6 diverse middle school students including Korean students listening attentively mid-lesson",
    "5 international high school students of mixed ethnicity collaborating over an open laptop",
    "7 diverse Korean and expat middle schoolers in school uniforms taking notes",
    "4 high school students (2 Korean, 2 other ethnicities) in a heated academic debate",
    "6 ethnically diverse middle schoolers conducting an experiment, safety goggles on",
    "5 Korean and multiracial high school students rehearsing lines for a school play",
    "8 diverse international school students playing team sport drills in the gym",
    "4 Korean high schoolers studying at individual desks under lamp light, fully focused",
    "6 international students including Korean teens practicing choreography in the dance room",
    "7 diverse middle school students building a robotics project on a worktable",
    "5 Korean and mixed-race teens in a music ensemble tuning their instruments",
    "8 high school students of diverse ethnicity in a lively classroom group discussion",
    "4 Korean high school students at computer stations writing code",
    "6 diverse international school students reading individually in the library",
    "7 Korean and expat middle schoolers at science lab benches examining slides",
    "5 international high school students working on an art piece together",
    "8 diverse middle schoolers at a group table for a project-based learning session",
    "4 Korean and multicultural teens in sports jerseys, water bottles in hand, post-training",
    "6 international school students watching a presentation by one of their peers",
    "7 diverse high school students in a debate circle, one at the podium speaking confidently",
    "5 Korean high schoolers reviewing SAT prep materials with color-coded notes",
    "8 mixed-ethnicity middle schoolers completing a science worksheet at their desks",
    "4 Korean and expat teens on the school stage, one in spotlight giving a speech",
    "6 international students in the makerspace, assembling a prototype together",
    "5 Korean high school students in study hall, heads down, pencils moving",
    "7 diverse teens in PE class stretching in formation",
    "4 Korean and multicultural high schoolers on a team playing basketball",
    "6 international students listening to a peer's music performance",
    "8 middle schoolers in a school cafeteria, chatting in English over lunch",
    "5 Korean high school students doing yoga poses in the mindfulness room",
    "7 international school students in ceramics studio shaping clay at the wheel",
    "4 diverse teens in the computer lab on a coding challenge",
    "6 Korean and multicultural high schoolers in the film production suite editing footage",
    "5 international school students in the innovation hub building a cardboard prototype",
    "8 diverse middle schoolers in the swimming pool during a team relay",
    "4 Korean teens reviewing notes together, one explaining to the others",
    "6 international students in orchestra rehearsal, bows raised",
    "7 Korean and expat high schoolers in ESL conversation class, speaking animatedly",
    "5 diverse teens in robotics lab, debugging their robot together",
    "8 high school students watching a science demonstration — all eyes wide",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-15  BOKEH / DEPTH-OF-FIELD DESCRIPTIONS  (20 items)
# ─────────────────────────────────────────────────────────────────────────────
BOKEH = [
    "the background students and environment are significantly blurred with creamy shallow depth-of-field bokeh",
    "the background melts into soft circular bokeh highlights, instructor razor-sharp",
    "beautiful f/1.4 bokeh renders background as smooth color washes",
    "shallow DOF keeps instructor in crisp focus while background dissolves into painterly blur",
    "background heavily blurred — soft orbs of colored light from classroom elements",
    "gentle lens falloff separates instructor from soft-focus background scene",
    "background students visible but blurred, creating layered three-dimensional depth",
    "extreme f/1.2 bokeh — background nearly abstract pastel color field",
    "medium blur on background retaining spatial context while prioritizing instructor",
    "background activity visible as impressionistic motion at f/2.0",
    "background warmly blurred into a wash of amber and cream tones",
    "cool blue background bokeh contrasts warm-lit instructor in foreground",
    "background windows render as soft white circles of light behind instructor",
    "greenery outside visible as soft emerald bokeh globes",
    "background lighting creates a naturally glowing halo behind the instructor",
    "stage lights behind instructor render as starburst bokeh on stopped-down aperture",
    "colorful classroom props visible but soft in background at f/1.8",
    "mirror wall behind creates infinite soft-focus depth",
    "overcast window light creates even fill while background fades to white",
    "background students seen as gentle silhouettes in warm blur",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-16  BRIDGE TEXT OVERLAY — FIXED (always the same)
# ─────────────────────────────────────────────────────────────────────────────
BRIDGE_OVERLAY_FIXED = (
    "The word 'BRIDGE' appears in clean white sans-serif letters, "
    "positioned at the center-left of the image. "
    "It is a plain text label only — no background panel, no shadow, no glow, no effects. "
    "The letters are sharp, flat, and white. "
    "It is NOT painted on a wall or any surface. "
    "It does NOT warp or distort with the scene. "
    "No other text, logos, or watermarks appear anywhere in the image."
)

# ─────────────────────────────────────────────────────────────────────────────
# DIM-17  CAMERA + LENS + TECHNICAL SPEC  (40 items)
# ─────────────────────────────────────────────────────────────────────────────
CAMERAS = [
    "Sony A9 III, 35mm f/1.4 Zeiss, ultra-sharp 4K, editorial photography",
    "Canon EOS R5, 50mm f/1.2L, 4K, cinematic bokeh, documentary style",
    "Nikon Z9, 85mm f/1.4 S, ultra-sharp 4K, photojournalism",
    "Sony FX3, 35mm f/1.8, 4K cinema, warm Sony color science",
    "Leica SL3, 50mm APO-Summicron, medium format rendering quality, 4K",
    "Fujifilm GFX100S, 63mm f/2.8, medium-format 4K, film-like rendering",
    "Canon EOS R3, 35mm f/1.4, 4K editorial, fast AF freezing motion",
    "Sony A7R V, 55mm f/1.8 Zeiss, 61MP downsampled 4K, ultimate sharpness",
    "Nikon Z8, 50mm f/1.2 S, 4K, natural Nikon color palette",
    "Canon EOS R6 Mark II, 35mm f/1.8 IS, 4K, warm color rendering",
    "Phase One IQ4, 80mm, medium format 4K rendering, extraordinary detail",
    "Sony A1, 24mm f/1.4 GM, 4K, ultra-wide immersive editorial",
    "Canon EOS R5C, 28mm f/2, 4K cinema, S-Log3 color grade applied",
    "Nikon D6, 50mm f/1.4G, 4K upscale, rich photojournalistic tone",
    "Sony A7S III, 35mm f/1.4, 4K, exceptional low-light rendering",
    "Hasselblad X2D, 45mm, medium format 4K quality, serene tones",
    "Sony FX6, 50mm f/1.4, 4K cinema, Venice color science applied",
    "Canon C70, 35mm f/1.8, 4K cinema, Canon Log3 grade",
    "Panasonic Lumix S5 II, 50mm f/1.4, 4K, warm European color science",
    "OM System OM-1 Mark II, 25mm f/1.2, 4K, vivid micro-four-thirds style",
    "Fujifilm X-T5, 56mm f/1.2, 4K, Eterna film simulation, filmic look",
    "Sony PXW-FX9, 50mm, 4K broadcast quality, natural skin tones",
    "Red Komodo, 35mm, 6K downsampled 4K, cinematic deep color",
    "Arri Alexa Mini, 40mm, cinema 4K, the gold standard for skin tones",
    "Blackmagic Pocket 6K G2, 25mm f/1.4, cinema 4K, Blackmagic Film grade",
    "Sony Venice 2, 50mm, cinema 4K, extraordinary dynamic range",
    "Canon EOS R7, 32mm f/1.4, crop-sensor 4K, punchy colors",
    "Nikon Z6 III, 50mm f/1.8 S, 4K, natural Nikon rendering",
    "Sony ZV-E1, 35mm, 4K, vlog-style color science with warm grade",
    "DJI Mavic 3 Pro Hasselblad, overhead indoor wide angle (gym/outdoor only)",
    "Sigma fp L, 45mm f/2.8, 61MP Cinema DNG 4K rendering",
    "Leica Q3, 28mm f/1.7, compact prime 4K, distinctive Leica rendering",
    "Canon R5 + 135mm f/2L, 4K telephoto compression, stunning bokeh",
    "Sony A7 IV, 85mm f/1.8, 4K, warm Sony rendering, flattering portrait",
    "Nikon Z5 II, 50mm f/1.8 S, 4K, color-accurate Nikon palette",
    "GoPro Hero 12 Black in Hero mode (only outdoor/sports context), 4K, wide-angle",
    "Canon EOS R8, 50mm f/1.8 STM, 4K, clean consumer-level sharpness",
    "Fujifilm X100VI, 23mm (equiv 35mm), 4K, Velvia film simulation",
    "Sony A6700, 16mm f/1.4, crop 4K, clean wide editorial",
    "Phase One XT with Rodenstock 40mm, technical-camera 4K quality, extreme sharpness",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-18  COLOR GRADING STYLE  (30 items)
# ─────────────────────────────────────────────────────────────────────────────
COLOR_GRADES = [
    "warm golden editorial color grade with lifted shadows",
    "clean neutral tone-mapped look — faithful true-to-life colors",
    "cinematic teal-and-orange color grade",
    "bright airy overexposed editorial look",
    "matte desaturated film-grade with cool shadows",
    "vivid saturated colors — advertising-grade retouching",
    "soft pastel palette — gentle greens and warm pinks",
    "Kodak Portra 400 film emulation — warm, grain, beautiful skin",
    "Fuji Velvia saturation with rich greens and blues",
    "Arri Alexa natural color science — skin tones paramount",
    "Sony Venice Venice-Look — clean, rich, cinematic",
    "slightly desaturated with warm skin-tone preservation",
    "clean corporate editorial grade — neutral, professional",
    "high-contrast black-and-white editorial (single promo image)",
    "cool morning light color grade — blue-white tones",
    "warm afternoon golden grade — amber highlights",
    "fashion editorial grade — slightly crushed blacks, clean whites",
    "documentary natural color — as-seen, minimal grade",
    "bright and clean — maximum clarity, no color cast",
    "split-tone: warm highlights, cool shadows",
    "flat and creamy — low contrast editorial style",
    "rich jewel tones — deep teals, warm ambers, saturated overall",
    "lifestyle photography grade — warm, bright, inviting",
    "magazine editorial standard — calibrated, precise, polished",
    "brand color alignment — subtle warmth that reads as 'trustworthy'",
    "Fuji Eterna Cinema simulation — natural, desaturated gracefully",
    "sunrise warm blush tone — pink-orange skin-friendly grade",
    "school photography standard — warm, clean, bright",
    "dark moody editorial — low-key, high contrast, deep shadows",
    "luminous soft-focus beauty grade — glow in highlights",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-19  ADDITIONAL PROP DETAILS  (40 items)
# ─────────────────────────────────────────────────────────────────────────────
PROPS = [
    "a large colorful world map poster visible on the side wall",
    "neatly organized bookshelves with colorful spines visible",
    "a globe on the teacher's desk catching the light",
    "stacked colorful textbooks on student desks",
    "a potted plant adding a touch of green near a window",
    "a vintage analog wall clock showing mid-morning time",
    "a motivational banner in English above the whiteboard",
    "children's artwork displayed in matching frames",
    "a collection of plastic educational models on a shelf",
    "a small digital camera on a tripod recording the lesson",
    "tablet devices on student desks, screen-on",
    "a bright yellow attendance board with student name cards",
    "an open piano with sheet music visible",
    "drums and a drum kit visible in the background",
    "colorful building blocks scattered on low shelves",
    "a weather chart with sun, cloud, and rain symbols in English",
    "a set of props — hats, bags, passports — for English role-play",
    "sports equipment (basketballs, cones) neatly stacked",
    "science fair display boards visible in background",
    "a digital smartboard showing a colorful lesson slide",
    "a class timetable chart on the side wall",
    "English vocabulary cards on a ring hanging from the whiteboard",
    "a cubbies rack with student labeled storage bins",
    "a large bean bag in one corner of the room",
    "a sensory bin filled with colored sand visible on a shelf",
    "two students' completed projects displayed on a table nearby",
    "an iPad stand with a visible language app running",
    "a cork board with pinned student work and gold-star stickers",
    "a standing easel with a half-finished student painting",
    "a mini-library trolley of English books parked near the wall",
    "a teacher's desk with a mug and open lesson plan book",
    "colourful rubber cones laid out in a pattern on gym floor",
    "a medal board showing achievement ribbons and trophies",
    "a class pet cage — small rabbit or hamster — visible on a counter",
    "a large number line frieze running at child eye level",
    "English country flags displayed along a bunting string",
    "a microscope visible on a lab bench in the background",
    "lab notebooks open on student tables",
    "an acoustic guitar leaning against the wall in a music room",
    "a mobile phone-filming rig capturing the class for online lesson",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-20  SEASON / TIME OF DAY ATMOSPHERE  (30 items)
# ─────────────────────────────────────────────────────────────────────────────
SEASONS = [
    "bright morning session, 9am light quality, clear day",
    "mid-morning class, 10:30am, clear spring light",
    "noon session, high sun, strong natural light",
    "after-school session, 4pm, warm afternoon light",
    "early evening class, sunset glow through windows",
    "rainy day — diffuse, cool, even interior light",
    "bright winter morning — cold clear light, blue sky outside",
    "autumn afternoon — warm amber light through golden leaves outside",
    "spring morning — soft fresh light, green visible outside",
    "summer noon — bleached-out bright exterior, interior slightly warm",
    "overcast grey day — flat even light, indoor warmth contrast",
    "early morning before students arrive — golden low preparatory light",
    "late afternoon golden hour slanting into classroom",
    "mid-morning after recess — students re-settled, warm steady light",
    "lunchtime light — warm bright, social energy in the atmosphere",
    "early winter afternoon — quick-to-darken sky, interior lighting prominent",
    "spring afternoon — cherry blossom haze of pink seen outside window",
    "stormy dramatic sky outside — moody interior contrast",
    "late morning, cloud patches creating dynamic light variation",
    "clear autumn morning — crisp cool blue light",
    "hot summer afternoon — strong overhead sun, shaded interior cool",
    "gentle fall afternoon — muted warm tones, leaves visible outside",
    "winter afternoon — snow visible outside windows, warm interior contrast",
    "after heavy rain — clean, washed light quality",
    "school open day morning — extra bright and well-prepared atmosphere",
    "exam season study hall — focused concentration in quiet mid-morning",
    "performance rehearsal evening — artificial light only, theatrical",
    "science fair day — heightened activity, bright full room lighting",
    "graduation morning — extraordinary care taken in presentation and light",
    "first day of new term — bright hopeful morning light",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-21  MOOD / ATMOSPHERE PHRASES  (30 items)
# ─────────────────────────────────────────────────────────────────────────────
MOODS = [
    "inspiring and aspirational — a place where futures are built",
    "warm and nurturing — every child feels seen and valued",
    "energetic and engaged — learning in motion",
    "focused and purposeful — serious academic intent",
    "joyful and expressive — creativity unleashed",
    "calm and contemplative — deep thinking rewarded",
    "collaborative and inclusive — no one left behind",
    "competitive but kind — pushing each other to grow",
    "playful and imaginative — learning through discovery",
    "professional and polished — preparing students for the world",
    "multicultural and welcoming — the world in one classroom",
    "innovative and forward-thinking — tomorrow's skills, today",
    "magical and immersive — education as adventure",
    "disciplined and proud — high standards upheld with care",
    "vibrant and multicultural — English as the bridge between cultures",
    "safe and encouraging — risk-taking in learning welcomed",
    "patient and supportive — every question is a good question",
    "dynamic and alive — no two moments the same",
    "rigorous and passionate — excellence pursued enthusiastically",
    "authentic and human — genuine connection between teacher and student",
    "globally minded — awareness of the wider world present throughout",
    "gritty and persevering — challenge embraced not avoided",
    "celebratory — achievements recognized in every lesson",
    "curious and questioning — Socratic atmosphere of inquiry",
    "bilingual bridge — seamlessly moving between Korean and English worlds",
    "digital-native friendly — technology as a natural extension of learning",
    "sensory-rich — learning that engages all five senses",
    "community-spirited — the classroom as a micro-society",
    "life-changing — the quiet sense that this moment matters",
    "BRIDGE-branded — quality, trust, and excellence personified",
]

# ─────────────────────────────────────────────────────────────────────────────
# DIM-22  QUALITY / REALISM MANDATES  (20 items)
# ─────────────────────────────────────────────────────────────────────────────
QUALITY_MANDATES = [
    "photorealistic human skin with visible pore detail, accurate anatomy",
    "no AI artifacts, no morphed hands, anatomically correct fingers",
    "editorial-grade retouching — natural skin, no plastic oversmoothing",
    "authentic candid energy — not overly posed or artificial",
    "accurate cultural authenticity — Korean school environment details correct",
    "highly detailed fabric textures on all clothing",
    "realistic eye catchlights and accurate pupil size",
    "natural hair texture and accurate hair flyaways",
    "correct Korean school signage and environment branding (Korean only if visible)",
    "accurate proportional rendering of children vs adults",
    "no uncanny valley — hyper-realistic without crossing into digital artificiality",
    "cinematic grain structure consistent with film-stock choice",
    "accurate depth of field falloff consistent with stated aperture",
    "faithful color accuracy — no impossible hues or neon overkill",
    "correct environmental physics — light sources match visible windows",
    "micro-expressions captured — authentic emotional realism",
    "architectural accuracy — room proportions and perspective correct",
    "no floating objects, correct gravity in scene",
    "correct scale and proportion of furniture for stated age group",
    "award-winning editorial photography quality throughout",
]

# ─────────────────────────────────────────────────────────────────────────────
# RULE COUNT SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
ALL_DIMS = {
    "DIM-01 Floors": FLOORS,
    "DIM-02 Walls": WALLS,
    "DIM-03 Ceilings": CEILINGS,
    "DIM-04 Ambient Lighting": LIGHTING_AMBIENT,
    "DIM-05 Instructor Race+Gender": INSTRUCTOR_RG,
    "DIM-06 Hair Styles": HAIR,
    "DIM-07 Upper Clothing": UPPER_CLOTHING,
    "DIM-08 Poses/Gestures": POSES,
    "DIM-09 Facial Expressions": EXPRESSIONS,
    "DIM-10 Age Descriptors": AGES,
    "DIM-11 Early Places": PLACES_EARLY,
    "DIM-12 Middle Places": PLACES_MIDDLE,
    "DIM-13 Students (Early)": STUDENTS_EARLY,
    "DIM-14 Students (Middle)": STUDENTS_MIDDLE,
    "DIM-15 Bokeh Descriptions": BOKEH,
    "DIM-16 BRIDGE Overlay": ["FIXED — always the same clean white label"],
    "DIM-17 Cameras": CAMERAS,
    "DIM-18 Color Grades": COLOR_GRADES,
    "DIM-19 Props": PROPS,
    "DIM-20 Season/Time": SEASONS,
    "DIM-21 Mood Phrases": MOODS,
    "DIM-22 Quality Mandates": QUALITY_MANDATES,
}


# =============================================================================
# ASSEMBLER
# =============================================================================

def assemble_prompt(target: str) -> dict:
    """
    Pick one item from each relevant dimension and assemble a complete prompt.
    target: 'early' | 'middle'
    """
    if target == "early":
        place = random.choice(PLACES_EARLY)
        students = random.choice(STUDENTS_EARLY)
    else:
        place = random.choice(PLACES_MIDDLE)
        students = random.choice(STUDENTS_MIDDLE)

    rg = random.choice(INSTRUCTOR_RG)
    race, gender = rg

    floor = random.choice(FLOORS)
    wall = random.choice(WALLS)
    ceiling = random.choice(CEILINGS)
    lighting = random.choice(LIGHTING_AMBIENT)
    hair = random.choice(HAIR)
    clothing = random.choice(UPPER_CLOTHING)
    pose = random.choice(POSES)
    expression = random.choice(EXPRESSIONS)
    age = random.choice(AGES)
    bokeh = random.choice(BOKEH)
    overlay = BRIDGE_OVERLAY_FIXED
    camera = random.choice(CAMERAS)
    grade = random.choice(COLOR_GRADES)
    prop = random.choice(PROPS)
    season = random.choice(SEASONS)
    mood = random.choice(MOODS)
    quality = random.choice(QUALITY_MANDATES)

    prompt = f"""Photorealistic 4K editorial photograph.

SETTING: {place["desc"]}. {floor}. {wall}. {ceiling}. {prop}.

TIME & ATMOSPHERE: {season}. {lighting}. Mood: {mood}.

FOREGROUND INSTRUCTOR: A {race} {gender} instructor, {age}, with {hair}, wearing {clothing}. {pose}. {expression}.

BACKGROUND STUDENTS: {students}. {bokeh}.

TEXT OVERLAY: {overlay}.

TECHNICAL: {camera}. Color grade: {grade}. {quality}. Aspect ratio 16:9. Award-winning editorial education photography. Absolutely NO other text, watermarks, or logos in the image besides the BRIDGE label."""

    return {
        "target": "Early Childhood" if target == "early" else "Middle/High School",
        "place": place["name"],
        "instructor": f"{race} {gender}",
        "prompt": prompt,
    }


def generate_batch(count: int, target: str | None = None) -> list[dict]:
    results = []
    targets = (["early"] * (count // 2) + ["middle"] * (count - count // 2)
               if target is None
               else [target] * count)
    random.shuffle(targets)
    for t in targets:
        results.append(assemble_prompt(t))
    return results


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="BRIDGE 4K Reality Prompt Generator v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-n", "--count", type=int, default=5)
    parser.add_argument("-t", "--target", choices=["early", "middle", "all"], default="all")
    parser.add_argument("-o", "--output", type=str)
    parser.add_argument("--stats", action="store_true", help="show rule counts per dimension")
    args = parser.parse_args()

    if args.stats:
        total = 0
        print("\nBRIDGE Prompt Generator - Rule Bank Stats")
        print("-" * 50)
        for dim, lst in ALL_DIMS.items():
            n = len(lst)
            total += n
            print(f"  {dim:<35} {n:>4} rules")
        print("-" * 50)
        print(f"  {'TOTAL':<35} {total:>4} rules")
        # Theoretical combinations
        dims_used = [
            FLOORS, WALLS, CEILINGS, LIGHTING_AMBIENT,
            INSTRUCTOR_RG, HAIR, UPPER_CLOTHING, POSES, EXPRESSIONS, AGES,
            BOKEH, CAMERAS, COLOR_GRADES,
            PROPS, SEASONS, MOODS, QUALITY_MANDATES,
        ]
        combos = 1
        for d in dims_used:
            combos *= len(d)
        print(f"\n  Theoretical unique combinations: {combos:,.0f}")
        return

    target = None if args.target == "all" else args.target
    prompts = generate_batch(args.count, target)

    lines = []
    lines.append("=" * 78)
    lines.append(f"  BRIDGE Prompt Generator v2.0 -- {datetime.now().strftime('%Y.%m.%d %H:%M')}")
    lines.append(f"  Generated: {len(prompts)}  |  Target: {args.target}")
    lines.append("=" * 78)

    for i, p in enumerate(prompts, 1):
        lines.append(f"\n{'-' * 60}")
        lines.append(f"  [{i}] {p['target']}  |  {p['place']}  |  {p['instructor']}")
        lines.append(f"{'-' * 60}")
        lines.append(p["prompt"])

    lines.append(f"\n{'=' * 78}")
    lines.append("  Copy & paste prompts into Midjourney / DALL-E 3 / Ideogram / Stable Diffusion")
    lines.append("=" * 78)

    output = "\n".join(lines)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"OK {len(prompts)} prompts saved: {args.output}")
    else:
        # stdout safe output
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(output)


if __name__ == "__main__":
    main()
