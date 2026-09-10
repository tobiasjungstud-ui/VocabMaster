"""Erkennung von Doppelungen, Wortfamilien und semantischen Überschneidungen.

Vier Ebenen, von der billigsten zur teuersten:

1. identische Stichwörter
2. Wortfamilien (``recycle`` / ``recycling`` / ``recycled``)
3. Bedeutungsgleichheit über die deutsche Übersetzung
   (``convince`` und ``persuade`` sind beide "überzeugen")
4. semantische Nähe durch das Sprachmodell (optional)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .models import Candidate
from .normalize import german_glosses, normalize_key, same_family

GLOSS_OVERLAP_THRESHOLD = 0.86


@dataclass
class Cluster:
    """Eine Gruppe von Kandidaten, die denselben Lerninhalt prüfen."""

    members: list[Candidate] = field(default_factory=list)
    reason: str = ""

    @property
    def best(self) -> Candidate:
        """Der Vertreter mit dem höchsten Lernwert."""
        return max(self.members, key=lambda c: (c.learning_value, c.difficulty))

    @property
    def rejected(self) -> list[Candidate]:
        keep = self.best
        return [m for m in self.members if m is not keep]


def _gloss_conflict(a: Candidate, b: Candidate) -> bool:
    """Prüfen zwei Einträge dieselbe deutsche Bedeutung ab?"""
    ga = {normalize_key(g) for g in german_glosses(a.german) if len(g) > 2}
    gb = {normalize_key(g) for g in german_glosses(b.german) if len(g) > 2}
    if not ga or not gb:
        return False
    if ga & gb:
        return True
    for x in ga:
        for y in gb:
            if len(x) > 4 and len(y) > 4:
                if SequenceMatcher(None, x, y).ratio() >= GLOSS_OVERLAP_THRESHOLD:
                    return True
    return False


def overlap_reason(a: Candidate, b: Candidate) -> str | None:
    """Warum kollidieren zwei Kandidaten - oder ``None``, wenn sie es nicht tun."""
    ka, kb = normalize_key(a.headword), normalize_key(b.headword)
    if not ka or not kb:
        return None
    if ka == kb:
        return "identisches Stichwort"
    if same_family(a.headword, b.headword):
        return "gleiche Wortfamilie"
    if _gloss_conflict(a, b):
        return "gleiche deutsche Bedeutung"
    return None


def cluster_candidates(candidates: list[Candidate]) -> list[Cluster]:
    """Gruppiert alle Kandidaten, die denselben Lerninhalt abdecken (Union-Find)."""
    parent = list(range(len(candidates)))
    reasons: dict[int, str] = {}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int, why: str) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri
            reasons.setdefault(ri, why)

    # Vorfilter über den Anfangsbuchstaben-Bucket wäre unzuverlässig
    # (Bedeutungsgleichheit ist orthografieunabhängig) - der Pool ist klein genug.
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            why = overlap_reason(candidates[i], candidates[j])
            if why:
                union(i, j, why)

    groups: dict[int, list[Candidate]] = defaultdict(list)
    for idx, c in enumerate(candidates):
        groups[find(idx)].append(c)

    return [
        Cluster(members=members, reason=reasons.get(root, "identisches Stichwort"))
        for root, members in groups.items()
    ]


def deduplicate(candidates: list[Candidate]) -> tuple[list[Candidate], list[tuple[Candidate, Candidate, str]]]:
    """Behält je Cluster den besten Kandidaten.

    Gibt die bereinigte Liste und die verworfenen Paare
    ``(verworfen, behalten, grund)`` zurück.
    """
    kept: list[Candidate] = []
    dropped: list[tuple[Candidate, Candidate, str]] = []
    for cluster in cluster_candidates(candidates):
        winner = cluster.best
        kept.append(winner)
        for loser in cluster.rejected:
            dropped.append((loser, winner, cluster.reason))
    kept.sort(key=lambda c: (-c.learning_value, c.headword.lower()))
    return kept, dropped


def find_cross_overlaps(
    test1: list[Candidate], test2: list[Candidate]
) -> list[tuple[Candidate, Candidate, str]]:
    """Alle unerwünschten Überschneidungen zwischen den beiden Tests."""
    hits = []
    for a in test1:
        for b in test2:
            why = overlap_reason(a, b)
            if why:
                hits.append((a, b, why))
    return hits


def find_internal_overlaps(items: list[Candidate]) -> list[tuple[Candidate, Candidate, str]]:
    """Überschneidungen innerhalb eines einzelnen Tests."""
    hits = []
    for i, a in enumerate(items):
        for b in items[i + 1 :]:
            why = overlap_reason(a, b)
            if why:
                hits.append((a, b, why))
    return hits


def topic_key(c: Candidate) -> str:
    """Grobe thematische Zuordnung über die Herkunftssektion."""
    return (c.section or "").strip().lower() or "allgemein"
