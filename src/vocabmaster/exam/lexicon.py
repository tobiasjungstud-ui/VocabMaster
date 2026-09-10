"""Small word lists used by the checker.  Deliberately tiny and editable."""

# Words that may legitimately repeat in a short text without it being sloppy.
FUNCTION_WORDS = set("""
a an the and or but so because if when while after before during until since
that this these those there here it its it's he she they we you i him her them
us my your his our their me
is are was were be been being am do does did done have has had having
will would can could shall should may might must
of in on at to for from with without about into over under between around
by as than then too very really quite much many more most some any no not
one two three four five first next last other another own same
go goes went get gets got make makes made take takes took come comes came
say says said see sees saw know knows knew think thinks thought want wants
like likes liked feel feels felt find finds found give gives gave tell tells
told use uses used try tries tried put puts keep keeps kept let lets
what which who whom whose why how where whether
all both each every few little lot lots enough
day days time times week weeks month months year years people person thing things
good bad big small new old long short great nice hard easy
""".split())

# Typical film / story vocabulary that carries a short text without being tested.
TOPIC_CARRIER_WORDS = set("""
film films movie movies cinema story stories book books series episode
watch watched watching read reading class school friend friends family
""".split())

# Grammatical slots: what has to follow these tokens.
BASE_VERB_TRIGGERS = {
    "to", "should", "must", "can", "could", "will", "would", "may", "might",
    "shall", "let", "help", "don't", "doesn't", "didn't", "do", "does", "did",
    "'ll", "cannot", "never",
}
NOUN_TRIGGERS = {
    "the", "a", "an", "this", "that", "these", "those", "my", "your", "his",
    "her", "its", "our", "their", "some", "any", "no", "every", "each",
    "another", "one", "of", "about",
}
ADJ_TRIGGERS = {
    "very", "really", "quite", "so", "too", "rather", "more", "most", "less",
    "is", "are", "was", "were", "be", "been", "look", "looks", "looked",
    "seem", "seems", "seemed", "feel", "feels", "felt", "become", "becomes",
    "became", "sound", "sounds", "sounded", "completely", "totally", "pretty",
    "extremely", "absolutely",
}
GERUND_TRIGGERS = {"avoid", "enjoy", "finish", "keep", "mind", "practise", "suggest",
                   "after", "before", "without", "by", "of"}

# Suffixes stripped when comparing two English words for a shared word family.
DERIVATION_SUFFIXES = (
    "ations", "ation", "ications", "ication", "ements", "ement", "nesses",
    "ness", "ities", "ity", "ings", "ing", "ives", "ive", "ally", "ance",
    "ence", "ers", "ors", "est", "ies", "ied", "ial", "ful", "ous", "ary",
    "ise", "ize", "ily", "al", "er", "or", "ed", "es", "ly", "y", "s",
)

# Pairs/groups that string comparison cannot catch but that confuse learners.
# Extend freely - one group per line, words as they appear in the vocabulary list.
DEFAULT_CONFUSABLE_GROUPS = [
    ["audience", "viewer", "spectator"],
    ["premiere", "release"],
    ["subtitles", "dubbed"],
    ["plot", "storyline", "story"],
    ["setting", "scene"],
    ["cast", "actor", "star"],
    ["award", "nomination", "nominate", "prize"],
    ["sequel", "episode"],
    ["review", "recommendation", "recommend"],
    ["effect", "special effect"],
    ["script", "screenplay"],
    ["act", "perform", "performance"],
    ["animation", "special effect"],
    ["gripping", "entertaining", "humour"],
    ["anxiety", "suffer", "recover"],
    ["journey", "adventure"],
    ["main character", "villain", "hero"],
    ["mixture", "adaptation"],
    ["display", "show", "present", "exhibit"],
    ["direct", "produce", "director"],
    ["soundtrack", "music", "song"],
    ["premiere", "opening"],
    ["script", "dialogue", "screenplay"],
    ["rewind", "replay"],
    ["dubbed", "translated"],
]

# German giveaways in an English text - a sentence that slipped through untranslated.
GERMAN_MARKERS = set("""
der die das den dem des ein eine einen einem einer eines und oder aber
ist sind war waren wird werden nicht kein keine auch noch schon sehr
ich du er sie es wir ihr mit für ohne bei nach vor zum zur beim
""".split())
