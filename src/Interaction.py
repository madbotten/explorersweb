"""
Interaction.py — Step 2

Defines the Interaction class and its resolve() method, which drives social
interactions between Characters on the same team.

Privacy levels : PRIVATE | PUBLIC
Setting types  : PERSONAL | PROFESSIONAL
    In PROFESSIONAL interactions characters are more tolerant of interaction
    types they dislike, and team leaders may add a bonus to success chances.

The observer_list parameter is accepted by resolve() but intentionally
ignored in Step 2; Step 3 will add observer effects.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    # Avoid circular import at runtime; Character is only needed for type hints.
    from Character import Character

# Import constants from Character at runtime inside functions to avoid
# circular-import problems (Character.py imports from Battle, Utils, Item).
# We re-export them here for convenience.
from Character import InteractionType, INTERACTION_LOVE_THRESHOLD, INTERACTION_HATE_THRESHOLD

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

PRIVATE  = "PRIVATE"
PUBLIC   = "PUBLIC"

PERSONAL     = "PERSONAL"
PROFESSIONAL = "PROFESSIONAL"

# In PROFESSIONAL settings, negative interaction_liked_by scores are
# multiplied by this factor (characters are more forgiving on the job).
PROFESSIONAL_TOLERANCE = 0.5

# How much the relationship score changes on a positive / negative outcome.
RELATIONSHIP_DELTA_SUCCESS = 5
RELATIONSHIP_DELTA_FAILURE = 3

# Morale change on success / failure (non-robots only).
MORALE_DELTA_SUCCESS = 3
MORALE_DELTA_FAILURE = 2

# Fraction of the team leader's leadership stat added as a threshold
# bonus in PROFESSIONAL interactions.
LEADERSHIP_BONUS_FRACTION = 0.10

# ---------------------------------------------------------------------------
# Object sentence fragment pools
# ---------------------------------------------------------------------------

_FLATTER_OBJECTS = [
    "about your outstanding leadership",
    "about your impressive skills",
    "about how decisive you are",
    "about your excellent judgment in the field",
    "about your tactical brilliance",
    "about the respect you command",
    "about your clear thinking under pressure",
    "about what an asset you are to this team",
]

# BRAG fragments are built dynamically from the initiator's skills/stats;
# these are fallback strings used when no skills are available.
_BRAG_STAT_NAMES = [
    "strength", "intelligence", "willpower",
    "coordination", "charisma", "courage",
]
_BRAG_FALLBACKS = [
    "their many accomplishments",
    "their impressive record",
    "how well they handled the last mission",
]

_PERSUADE_OBJECTS = [
    "take the first watch",
    "share their rations",
    "reconsider the plan",
    "back down from the argument",
    "support the team's decision",
    "volunteer for the dangerous task",
    "lend their expertise to the group",
    "change their approach",
    "accept a different assignment",
]

_THREATEN_OBJECTS = [
    "to stay out of their way",
    "not to cross them again",
    "to keep quiet about what they saw",
    "to comply or face consequences",
    "to think carefully before acting against them",
]

_DEMAND_OBJECTS = [
    "man a watch station",
    "follow orders immediately",
    "complete the assigned mission task",
    "report to their post",
    "hand over the supplies",
    "stand down from the argument",
    "carry out the directive without question",
]

_REQUEST_OBJECTS = [
    "fabricate an item",
    "cover their position",
    "share their intel",
    "assist with the repairs",
    "keep an eye on the perimeter",
    "help plan the approach",
    "lend a hand with the equipment",
    "watch their back during the operation",
]

# INFORM objects are built from initiator skills; this is a fallback list.
_INFORM_FALLBACKS = [
    "ship navigation",
    "general mission protocols",
    "local sector hazards",
]

# JOKE topics; per-character skill jokes are added dynamically.
_JOKE_TOPICS_GENERIC = [
    "their terrible luck with equipment",
    "a memorable blunder on the last mission",
    "questionable fashion choices",
    "the time someone got hopelessly lost",
    "that infamous incident at the starport",
    "the crew's rivalry with the other squad",
    "the ship's ancient coffee maker",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _choose_interaction_type(initiator: "Character", privacy_level: str) -> str:
    """
    Choose a weighted-random interaction type.

    Weight = max(1, 50 + initiator.interaction_likes[type]).
    THREATEN is only available to psychotic initiators in PRIVATE settings.
    """
    weights: dict[str, int] = {}
    for itype in InteractionType.ALL:
        score = initiator.interaction_likes.get(itype, 0)
        weights[itype] = max(1, 50 + score)

    # THREATEN is only allowed for psychotic characters in private settings.
    if not (getattr(initiator, "psychotic", False) and privacy_level == PRIVATE):
        weights[InteractionType.THREATEN] = 0

    eligible = [t for t in InteractionType.ALL if weights[t] > 0]
    w_values = [weights[t] for t in eligible]

    if not eligible:
        return InteractionType.INFORM  # safe fallback

    return random.choices(eligible, weights=w_values, k=1)[0]


def _brag_object(initiator: "Character") -> str:
    """Build an object fragment for a BRAG interaction."""
    options: list[str] = []

    if initiator.skills:
        skill = random.choice(list(initiator.skills.keys()))
        score = initiator.skills[skill]
        options.append(f"their {skill} skills")
        options.append(f"their {skill} score of {score}")

    stat = random.choice(_BRAG_STAT_NAMES)
    stat_val = initiator.stats.get(stat, 0)
    options.append(f"their impressive {stat} ({stat_val})")

    return random.choice(options) if options else random.choice(_BRAG_FALLBACKS)


def _inform_object(initiator: "Character") -> str:
    """Build an object fragment for an INFORM interaction (one of initiator's skills)."""
    if initiator.skills:
        skill = random.choice(list(initiator.skills.keys()))
        return skill.lower()
    return random.choice(_INFORM_FALLBACKS)


def _joke_object(initiator: "Character", target: "Character") -> str:
    """Build an object fragment for a JOKE interaction."""
    options = list(_JOKE_TOPICS_GENERIC)

    if initiator.skills:
        skill = random.choice(list(initiator.skills.keys()))
        options.append(f"{initiator.name}'s {skill.lower()} skills")

    if target.skills:
        skill = random.choice(list(target.skills.keys()))
        options.append(f"{target.name}'s {skill.lower()} skills")

    return random.choice(options)


def _build_sentence(initiator: "Character", target: "Character", interaction_type: str) -> str:
    """
    Build a UI-ready sentence describing the interaction.

    Patterns:
        FLATTER  : {I} FLATTERED {T} {object}.
        BRAG     : {I} BRAGGED to {T} about {object}.
        PERSUADE : {I} PERSUADED {T} to {object}.
        THREATEN : {I} THREATENED {T} {object}.
        DEMAND   : {I} DEMANDED {T} {object}.
        INFORM   : {I} INFORMED {T} about {object}.
        REQUEST  : {I} REQUESTED {T} {object}.
        JOKE     : {I} JOKED with {T} about {object}.
    """
    iname = initiator.name
    tname = target.name

    if interaction_type == InteractionType.FLATTER:
        obj = random.choice(_FLATTER_OBJECTS)
        return f"{iname} FLATTERED {tname} {obj}."

    if interaction_type == InteractionType.BRAG:
        obj = _brag_object(initiator)
        return f"{iname} BRAGGED to {tname} about {obj}."

    if interaction_type == InteractionType.PERSUADE:
        obj = random.choice(_PERSUADE_OBJECTS)
        return f"{iname} PERSUADED {tname} to {obj}."

    if interaction_type == InteractionType.THREATEN:
        obj = random.choice(_THREATEN_OBJECTS)
        return f"{iname} THREATENED {tname} {obj}."

    if interaction_type == InteractionType.DEMAND:
        obj = random.choice(_DEMAND_OBJECTS)
        return f"{iname} DEMANDED {tname} {obj}."

    if interaction_type == InteractionType.INFORM:
        obj = _inform_object(initiator)
        return f"{iname} INFORMED {tname} about {obj}."

    if interaction_type == InteractionType.REQUEST:
        obj = random.choice(_REQUEST_OBJECTS)
        return f"{iname} REQUESTED {tname} {obj}."

    if interaction_type == InteractionType.JOKE:
        obj = _joke_object(initiator, target)
        return f"{iname} JOKED with {tname} about {obj}."

    # Fallback (should never be reached)
    return f"{iname} interacted with {tname}."


def _get_leadership_bonus(initiator: "Character", target: "Character") -> int:
    """
    Find the highest-leadership non-robot character in the team shared by
    initiator and target, and return LEADERSHIP_BONUS_FRACTION of their score.
    """
    team = getattr(initiator, "team", None) or []
    best = 0
    for member in team:
        if not getattr(member, "is_robot", lambda: False)():
            ldr = member.stats.get("leadership", 0)
            if ldr > best:
                best = ldr
    return int(best * LEADERSHIP_BONUS_FRACTION)


def _calculate_threshold(
    initiator: "Character",
    target: "Character",
    interaction_type: str,
    setting_type: str,
) -> int:
    """
    Compute the success threshold for a d100 roll (success if roll < threshold).

    Base threshold: 50 (even odds).

    Modifiers (all scaled to avoid swamping the base):
      +/- liked_by_score // 5   (target's preference for this interaction type)
      +/- relationship   // 5   (target's existing feeling toward initiator)
      +   leadership bonus      (PROFESSIONAL only, from team leader)

    In PROFESSIONAL setting, negative liked_by scores are dampened.
    """
    threshold = 50

    # --- Target's preference for this kind of interaction ---
    liked_by = target.interaction_liked_by.get(interaction_type, 0)
    if setting_type == PROFESSIONAL and liked_by < 0:
        liked_by = int(liked_by * (1.0 - PROFESSIONAL_TOLERANCE))
    threshold += liked_by // 5

    # --- Target's existing relationship with initiator ---
    threshold += target.get_relationship(initiator.name) // 5

    # --- Leadership bonus (PROFESSIONAL only) ---
    if setting_type == PROFESSIONAL:
        threshold += _get_leadership_bonus(initiator, target)

    return threshold


# ---------------------------------------------------------------------------
# Interaction class
# ---------------------------------------------------------------------------

class Interaction:
    """
    Encapsulates a resolved social interaction between two Characters.

    Typical usage::

        result = Interaction.resolve(
            initiator, target, observer_list,
            setting_type=PROFESSIONAL,
            privacy_level=PUBLIC,
        )
        print(result.sentence)
        print("Success!" if result.success else "Failed.")
    """

    def __init__(
        self,
        *,
        sentence: str,
        success: bool,
        interaction_type: str,
        roll: int,
        threshold: int,
    ):
        self.sentence         = sentence
        self.success          = success
        self.interaction_type = interaction_type
        self.roll             = roll
        self.threshold        = threshold

    def __repr__(self) -> str:
        outcome = "success" if self.success else "failure"
        return (
            f"Interaction(type={self.interaction_type}, {outcome}, "
            f"roll={self.roll}, threshold={self.threshold})"
        )

    # ------------------------------------------------------------------

    @staticmethod
    def resolve(
        initiator: "Character",
        target: "Character",
        observer_list: List["Character"],
        setting_type: str,
        privacy_level: str,
    ) -> "Interaction":
        """
        Resolve a social interaction between *initiator* and *target*.

        Parameters
        ----------
        initiator     : Character attempting the interaction.
        target        : Character receiving the interaction.
        observer_list : Other characters who witness it (ignored in Step 2).
        setting_type  : PERSONAL or PROFESSIONAL.
        privacy_level : PRIVATE or PUBLIC.

        Returns
        -------
        Interaction instance describing what happened and its outcome.

        Side-effects
        ------------
        On success the target's relationship with the initiator is nudged up
        and their morale is encouraged (non-robots only).
        On failure the relationship and morale are nudged down (non-robots only).
        Robotic targets are immune to all relationship and morale changes.
        """

        # 1. Choose which interaction type the initiator performs.
        interaction_type = _choose_interaction_type(initiator, privacy_level)

        # 2. Build the narrative sentence for the game UI.
        sentence = _build_sentence(initiator, target, interaction_type)

        # 3. Roll for success.
        roll      = random.randint(1, 100)
        threshold = _calculate_threshold(initiator, target, interaction_type, setting_type)
        success   = roll < threshold

        # 4. Apply outcomes to (non-robot) target.
        target_is_robot = getattr(target, "is_robot", lambda: False)()
        if not target_is_robot:
            if success:
                target.adjust_relationship(initiator.name, RELATIONSHIP_DELTA_SUCCESS)
                target.encourage(MORALE_DELTA_SUCCESS)
            else:
                target.adjust_relationship(initiator.name, -RELATIONSHIP_DELTA_FAILURE)
                target.demoralize(MORALE_DELTA_FAILURE)

        # observer_list intentionally unused here — Step 3 will add observer effects.

        return Interaction(
            sentence=sentence,
            success=success,
            interaction_type=interaction_type,
            roll=roll,
            threshold=threshold,
        )
