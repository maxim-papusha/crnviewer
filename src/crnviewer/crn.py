from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Hashable, Iterable, Iterator, MutableSet, Set
from typing import Generic, TypeVar

from stereomolgraph import (
    CondensedReactionGraph,
    MolGraph,
    StereoCondensedReactionGraph,
    StereoMolGraph,
)

R = TypeVar("R", bound=Hashable)
S = TypeVar("S", bound=Hashable, covariant=True)


class BaseReactionContainer(Generic[R, S], MutableSet[R], ABC):
    """Abstract base for reaction networks."""

    _species_mapping: dict[S, set[R]]
    _reactions_mapping: dict[R, tuple[tuple[S, ...], tuple[S, ...]]]

    @staticmethod
    @abstractmethod
    def reactants_and_products_from_reaction(
        reaction: R,
    ) -> tuple[tuple[S, ...], tuple[S, ...]]:
        """Return (reactants, products) tuple extracted from a reaction."""
        ...

    def __init__(self, reactions: Iterable[R] | None = None) -> None:
        """Initialize internal mappings.

        Optionally seed the network with an iterable of reactions.
        Concrete subclasses must implement `species_from_reaction`.
        """
        self._species_mapping = defaultdict(set)
        self._reactions_mapping = dict()
        if reactions is not None:
            for r in set(reactions):
                self.add(r)

    @property
    def species(self) -> Set[S]:
        return frozenset(self._species_mapping.keys())

    @property
    def reactions(self) -> Set[R]:
        return frozenset(self._reactions_mapping.keys())

    # MutableSet abstract methods
    def __contains__(self, reaction: object) -> bool:
        return reaction in self._reactions_mapping

    def __iter__(self) -> Iterator[R]:
        return iter(self._reactions_mapping.keys())

    def __len__(self) -> int:
        return len(self._reactions_mapping)

    def add(self, value: R) -> None:
        """Add a reaction and update species mappings.

        Uses `species_from_reaction` to extract species. If the reaction
        already exists, this is a no-op.
        """
        if value in self._reactions_mapping:
            return

        reactants, products = self.reactants_and_products_from_reaction(value)
        self._reactions_mapping[value] = (reactants, products)
        for s in itertools.chain(reactants, products):
            self._species_mapping[s].add(value)

    def discard(self, value: R) -> None:
        """Remove a reaction if present and update species mappings."""
        if value not in self._reactions_mapping:
            return

        reactants, products = self._reactions_mapping.pop(value)
        for s in itertools.chain(reactants, products):
            species_reactions = self._species_mapping[s]
            species_reactions.discard(value)
            if not species_reactions:
                # remove species entry when no reactions reference it
                del self._species_mapping[s]


class CRGContainer(BaseReactionContainer[CondensedReactionGraph, MolGraph]):
    """Concrete network storing `CondensedReactionGraph` reactions and
    tracking `MolGraph` species.
    """

    @staticmethod
    def reactants_and_products_from_reaction(
        reaction: CondensedReactionGraph,
    ) -> tuple[tuple[MolGraph, ...], tuple[MolGraph, ...]]:
        reactants_graph = reaction.reactant()
        reactants = tuple(
            reactants_graph.subgraph(atoms)
            for atoms in reactants_graph.connected_components()
        )
        products_graph = reaction.product()
        products = tuple(
            products_graph.subgraph(atoms)
            for atoms in products_graph.connected_components()
        )
        return reactants, products


class SCRGContainer(
    BaseReactionContainer[StereoCondensedReactionGraph, StereoMolGraph]
):
    """Concrete network storing `MolGraph` reactions and tracking
    `StereoMolGraph` species.
    """

    @staticmethod
    def reactants_and_products_from_reaction(
        reaction: StereoCondensedReactionGraph,
    ) -> tuple[tuple[StereoMolGraph, ...], tuple[StereoMolGraph, ...]]:
        reactants_graph = reaction.reactant()
        reactants = tuple(
            reactants_graph.subgraph(atoms)
            for atoms in reactants_graph.connected_components()
        )
        products_graph = reaction.product()
        products = tuple(
            products_graph.subgraph(atoms)
            for atoms in products_graph.connected_components()
        )
        return reactants, products
