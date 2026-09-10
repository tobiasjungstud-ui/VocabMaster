"""Auswahl der 60 Wörter und ausgewogene Verteilung auf Test 1 und Test 2."""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from .dedup import overlap_reason, topic_key
from .leveling import is_hard_excluded
from .models import POS, Candidate

TARGET_TOTAL = 60
TEST_SIZE = 30

# Wie stark Häufungen einer Wortart bzw. eines Themas bestraft werden.
_POS_PENALTY = 0.055
_TOPIC_PENALTY = 0.085


@dataclass
class Selection:
    """Ergebnis der Auswahl inklusive Protokoll."""

    chosen: list[Candidate] = field(default_factory=list)
    relaxed: list[Candidate] = field(default_factory=list)
    deficit: int = 0
    notes: list[str] = field(default_factory=list)


def _diversity_score(
    c: Candidate,
    pos_counts: Counter,
    topic_counts: Counter,
    bias: Callable[[Candidate], float] | None = None,
) -> float:
    """Lernwert, abgewertet nach bereits gewählter Wortart und Thema.

    ``bias`` ist der Zuschlag des Niveaus: Niveau A zieht schwierigere,
    Niveau B zugänglichere Wörter nach vorn (siehe :mod:`vocabmaster.niveau`).
    """
    return (
        c.learning_value
        + (bias(c) if bias else 0.0)
        - _POS_PENALTY * pos_counts[c.pos]
        - _TOPIC_PENALTY * topic_counts[topic_key(c)]
    )


def _greedy_pick(
    pool: list[Candidate],
    target: int,
    seed: list[Candidate] | None = None,
    bias: Callable[[Candidate], float] | None = None,
) -> list[Candidate]:
    """Wählt ``target`` Kandidaten mit hohem Lernwert und guter Durchmischung."""
    chosen: list[Candidate] = list(seed or [])
    pos_counts = Counter(c.pos for c in chosen)
    topic_counts = Counter(topic_key(c) for c in chosen)
    remaining = [c for c in pool if c not in chosen]

    while remaining and len(chosen) < target:
        best = max(
            remaining,
            key=lambda c: (_diversity_score(c, pos_counts, topic_counts, bias), c.difficulty),
        )
        remaining.remove(best)
        if any(overlap_reason(best, c) for c in chosen):
            continue
        chosen.append(best)
        pos_counts[best.pos] += 1
        topic_counts[topic_key(best)] += 1
    return chosen


def select_words(
    usable: list[Candidate],
    fallback: list[Candidate] | None = None,
    target: int = TARGET_TOTAL,
    bias: Callable[[Candidate], float] | None = None,
) -> Selection:
    """Stellt möglichst genau ``target`` geeignete Wörter zusammen.

    Reicht der geprüfte Pool nicht aus, werden die am wenigsten problematischen
    aussortierten Wörter stufenweise wieder zugelassen ("Relaxation"), bevor ein
    Fehlbestand gemeldet wird, den die Ersatzwortsuche ausgleichen muss.
    """
    result = Selection()
    result.chosen = _greedy_pick(usable, target, bias=bias)

    if len(result.chosen) < target and fallback:
        # Stufenweise Lockerung: erst grenzwertig einfache Wörter,
        # dann Kognate, zuletzt seltene Wörter.
        ladder = [
            ("zu_einfach", "etwas zu einfach"),
            ("kognat", "dem Deutschen sehr ähnlich"),
            ("frueher_gelernt", "kam in einer früheren Unit vor"),
            ("zu_selten", "im Englischen wenig gebräuchlich"),
        ]
        for flag, label in ladder:
            if len(result.chosen) >= target:
                break
            extras = [
                c
                for c in fallback
                if flag in c.flags
                and c not in result.chosen
                and not is_hard_excluded(c)
            ]
            extras.sort(key=lambda c: (-(c.learning_value + (bias(c) if bias else 0.0)), -c.difficulty))
            for c in extras:
                if len(result.chosen) >= target:
                    break
                if any(overlap_reason(c, other) for other in result.chosen):
                    continue
                c.flag("aufgefuellt", f"Nachgerückt, weil der Pool zu klein war ({label}).")
                result.chosen.append(c)
                result.relaxed.append(c)
            if result.relaxed:
                result.notes.append(
                    f"{len(result.relaxed)} Wörter mussten nachrücken ({label})."
                )

    result.deficit = max(0, target - len(result.chosen))
    return result


# ---------------------------------------------------------------------------
# Aufteilung auf zwei gleichwertige Tests
# ---------------------------------------------------------------------------


def _distribution_cost(a: list[Candidate], b: list[Candidate]) -> float:
    """Je kleiner, desto ähnlicher sind die beiden Tests."""
    if not a or not b:
        return math.inf

    mean_a = sum(c.difficulty for c in a) / len(a)
    mean_b = sum(c.difficulty for c in b) / len(b)
    cost = 14.0 * abs(mean_a - mean_b)

    # Streuung ebenfalls angleichen, damit nicht ein Test nur Extreme enthält.
    def spread(xs: list[Candidate]) -> float:
        m = sum(c.difficulty for c in xs) / len(xs)
        return math.sqrt(sum((c.difficulty - m) ** 2 for c in xs) / len(xs))

    cost += 4.0 * abs(spread(a) - spread(b))

    # Wortarten gleichmässig verteilen.
    for pos in POS:
        ca = sum(1 for c in a if c.pos is pos)
        cb = sum(1 for c in b if c.pos is pos)
        cost += 0.25 * abs(ca - cb)

    # Thematisch zusammengehörende Begriffe auf beide Tests streuen.
    topics = {topic_key(c) for c in a + b}
    for t in topics:
        ca = sum(1 for c in a if topic_key(c) == t)
        cb = sum(1 for c in b if topic_key(c) == t)
        cost += 0.18 * abs(ca - cb)

    # Lernwert vergleichbar halten.
    va = sum(c.learning_value for c in a) / len(a)
    vb = sum(c.learning_value for c in b) / len(b)
    cost += 3.0 * abs(va - vb)
    return cost


def split_balanced(
    words: list[Candidate], test_size: int = TEST_SIZE, seed: int = 20240607
) -> tuple[list[Candidate], list[Candidate]]:
    """Teilt die Wörter in zwei gleich grosse, gleich schwere Hälften.

    Startpunkt ist eine "Schlangenverteilung" nach Schwierigkeit innerhalb
    jeder Wortart; anschliessend verbessern Tauschschritte die Balance.
    """
    rng = random.Random(seed)
    pool = list(words)
    if len(pool) < 2 * test_size:
        raise ValueError(
            f"Für zwei Tests werden {2 * test_size} Wörter benötigt, "
            f"vorhanden sind {len(pool)}."
        )
    pool = pool[: 2 * test_size]

    # 1) Schlangenverteilung je Wortart
    a: list[Candidate] = []
    b: list[Candidate] = []
    by_pos: dict[POS, list[Candidate]] = {}
    for c in pool:
        by_pos.setdefault(c.pos, []).append(c)
    toggle = 0
    for pos in sorted(by_pos, key=lambda p: -len(by_pos[p])):
        group = sorted(by_pos[pos], key=lambda c: -c.difficulty)
        for i, c in enumerate(group):
            target = a if (i + toggle) % 2 == 0 else b
            target.append(c)
        toggle = (toggle + len(group)) % 2

    # Grössen ausgleichen
    while len(a) > test_size:
        b.append(a.pop())
    while len(b) > test_size:
        a.append(b.pop())

    # 2) Lokale Verbesserung durch Tauschen
    best_cost = _distribution_cost(a, b)
    for _ in range(600):
        i = rng.randrange(len(a))
        j = rng.randrange(len(b))
        a[i], b[j] = b[j], a[i]
        cost = _distribution_cost(a, b)
        if cost < best_cost - 1e-9:
            best_cost = cost
        else:
            a[i], b[j] = b[j], a[i]  # Tausch zurücknehmen

    # Innerhalb eines Tests thematisch sortieren, damit die Liste ruhig wirkt.
    a.sort(key=lambda c: (topic_key(c), c.pos.value, c.headword.lower()))
    b.sort(key=lambda c: (topic_key(c), c.pos.value, c.headword.lower()))
    return a, b


def balance_summary(a: list[Candidate], b: list[Candidate]) -> dict[str, float]:
    """Kennzahlen für den Qualitätsbericht."""

    def mean(xs: list[Candidate], attr: str) -> float:
        return round(sum(getattr(c, attr) for c in xs) / len(xs), 3) if xs else 0.0

    return {
        "schwierigkeit_test1": mean(a, "difficulty"),
        "schwierigkeit_test2": mean(b, "difficulty"),
        "schwierigkeit_differenz": round(
            abs(mean(a, "difficulty") - mean(b, "difficulty")), 3
        ),
        "lernwert_test1": mean(a, "learning_value"),
        "lernwert_test2": mean(b, "learning_value"),
        "zipf_test1": mean(a, "zipf"),
        "zipf_test2": mean(b, "zipf"),
        "wortarten_test1": {p.value: sum(1 for c in a if c.pos is p) for p in POS},
        "wortarten_test2": {p.value: sum(1 for c in b if c.pos is p) for p in POS},
    }
