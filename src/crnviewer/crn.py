from __future__ import annotations

import itertools
from dataclasses import dataclass
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Hashable, Iterable, Iterator, MutableSet, Set
from typing import Any, Generic, TypeVar, cast

from .rdkit_render import (
    RDKitDrawOptions,
    remove_atom_maps_from_mol,
    remove_atom_maps_from_reaction,
)

try:
    from stereomolgraph import (
        CondensedReactionGraph,
        MolGraph,
        StereoCondensedReactionGraph,
        StereoMolGraph,
    )
    _HAS_STEREOMOLGRAPH = True
except Exception:  # pragma: no cover - optional dependency
    CondensedReactionGraph = Any  # type: ignore[assignment]
    MolGraph = Any  # type: ignore[assignment]
    StereoCondensedReactionGraph = Any  # type: ignore[assignment]
    StereoMolGraph = Any  # type: ignore[assignment]
    _HAS_STEREOMOLGRAPH = False

R = TypeVar("R", bound=Hashable)
S = TypeVar("S", bound=Hashable, covariant=True)


def _require_stereomolgraph() -> None:
    if not _HAS_STEREOMOLGRAPH:
        raise RuntimeError(
            "stereomolgraph is required for CRGContainer/SCRGContainer. "
            "Use RDKitMappedReactionContainer for RDKit-only workflows."
        )


def _iterable_or_single(value: str | Iterable[str]) -> Iterable[str]:
    if isinstance(value, str):
        return (value,)
    return value


def _combine_rdkit_mols(mols: list[Any]) -> Any:
    from rdkit import Chem

    if not mols:
        raise ValueError("At least one molecule is required")

    combined = Chem.Mol(mols[0])
    for mol in mols[1:]:
        combined = Chem.CombineMols(combined, mol)
    return combined


def _reaction_smiles_parts(
    mapped_reaction_smiles: str,
) -> tuple[str, str, str]:
    """Split ``reactants>agents>products`` reaction text into three parts.

    The ``agents`` segment is parsed for format validation only and is
    currently ignored by container-construction workflows.
    """

    parts = mapped_reaction_smiles.split(">")
    if len(parts) != 3:
        raise ValueError(
            "Reaction string must have reactants>agents>products format"
        )
    reactants, agents, products = (part.strip() for part in parts)
    return reactants, agents, products


def _mols_from_smiles_side(smiles_side: str) -> list[Any]:
    from rdkit import Chem

    chunks = [chunk.strip() for chunk in smiles_side.split(".") if chunk.strip()]
    if not chunks:
        raise ValueError("Reaction side must contain at least one molecule")

    mols: list[Any] = []
    for chunk in chunks:
        mol = Chem.MolFromSmiles(chunk, sanitize=False)
        if mol is None:
            raise ValueError(f"Could not parse SMILES: {chunk}")
        mols.append(mol)
    return mols


def _validate_mapped_reaction_mols(
    reactant_mol: Any,
    product_mol: Any,
) -> None:
    reactant_map = {
        atom.GetAtomMapNum(): atom.GetSymbol()
        for atom in reactant_mol.GetAtoms()
    }
    product_map = {
        atom.GetAtomMapNum(): atom.GetSymbol()
        for atom in product_mol.GetAtoms()
    }

    if 0 in reactant_map or 0 in product_map:
        raise ValueError(
            "Atom-mapped reactions require non-zero atom-map numbers "
            "on all reactant/product atoms"
        )

    if len(reactant_map) != reactant_mol.GetNumAtoms():
        raise ValueError("Reactant atom-map numbers must be unique")
    if len(product_map) != product_mol.GetNumAtoms():
        raise ValueError("Product atom-map numbers must be unique")

    if set(reactant_map) != set(product_map):
        raise ValueError(
            "Reactant and product atom-map numbers must match"
        )

    for map_num in reactant_map:
        if reactant_map[map_num] != product_map[map_num]:
            raise ValueError(
                "Atom-map numbers must preserve atom symbols across "
                "reactants and products"
            )


def _graphs_from_mapped_reaction_smiles(
    mapped_reaction_smiles: str,
    *,
    graph_type: type[MolGraph] | type[StereoMolGraph],
) -> tuple[MolGraph | StereoMolGraph, MolGraph | StereoMolGraph]:
    """Build reactant/product graph pair from atom-mapped reaction SMILES.

    Expects ``reactants>agents>products`` input. The middle ``agents`` block
    is currently ignored and is not represented in the generated container.
    """

    reactants, _agents, products = _reaction_smiles_parts(
        mapped_reaction_smiles
    )

    reactant_mol = _combine_rdkit_mols(_mols_from_smiles_side(reactants))
    product_mol = _combine_rdkit_mols(_mols_from_smiles_side(products))

    _validate_mapped_reaction_mols(reactant_mol, product_mol)

    reactant_graph = graph_type.from_rdmol(
        reactant_mol,
        use_atom_map_number=True,
    )
    product_graph = graph_type.from_rdmol(
        product_mol,
        use_atom_map_number=True,
    )
    return reactant_graph, product_graph


def _mapped_reaction_smiles_from_rdkit_reaction(reaction: Any) -> str:
    from rdkit.Chem import rdChemReactions

    mapped_smiles = rdChemReactions.ReactionToSmiles(reaction)
    if not isinstance(mapped_smiles, str) or ">>" not in mapped_smiles:
        raise ValueError("Could not serialize RDKit reaction to reaction SMILES")
    return mapped_smiles


@dataclass(frozen=True)
class RDKitSpecies:
    """Hashable species object for RDKit-only mapped-reaction workflows."""

    mapped_smiles: str


@dataclass(frozen=True)
class RDKitMappedReaction:
    """Hashable reaction object storing mapped reaction SMILES."""

    mapped_reaction_smiles: str


class RDKitMappedReactionRenderer:
    """Renderer that draws species and reactions as SVG using RDKit only."""

    def __init__(
        self,
        *,
        width: int = 300,
        height: int = 300,
        options: RDKitDrawOptions | None = None,
    ) -> None:
        self._width = width
        self._height = height
        self._options = options or RDKitDrawOptions()

    def svg(self, obj: Hashable) -> str:
        from rdkit import Chem
        from rdkit.Chem import rdChemReactions
        from rdkit.Chem.Draw import rdMolDraw2D

        if isinstance(obj, RDKitSpecies):
            mol = Chem.MolFromSmiles(obj.mapped_smiles, sanitize=False)
            if mol is None:
                raise ValueError(f"Could not parse species SMILES: {obj.mapped_smiles}")
            if not self._options.includeAtomMaps:
                mol = remove_atom_maps_from_mol(mol)
            drawer = rdMolDraw2D.MolDraw2DSVG(self._width, self._height)
            self._options.apply_to(drawer.drawOptions())
            rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
            drawer.FinishDrawing()
            return drawer.GetDrawingText()

        if isinstance(obj, RDKitMappedReaction):
            rxn = rdChemReactions.ReactionFromSmarts(
                obj.mapped_reaction_smiles,
                useSmiles=True,
            )
            if rxn is None:
                raise ValueError(
                    "Could not parse mapped reaction SMILES: "
                    f"{obj.mapped_reaction_smiles}"
                )
            if not self._options.includeAtomMaps:
                rxn = remove_atom_maps_from_reaction(rxn)
            drawer = rdMolDraw2D.MolDraw2DSVG(self._width, self._height)
            self._options.apply_to(drawer.drawOptions())
            drawer.DrawReaction(rxn)
            drawer.FinishDrawing()
            return drawer.GetDrawingText()

        raise TypeError(f"Unsupported object for RDKit rendering: {type(obj)!r}")


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


class RDKitMappedReactionContainer(
    BaseReactionContainer[RDKitMappedReaction, RDKitSpecies]
):
    """Reaction container for mapped reaction SMILES without stereomolgraph.

    Species and reactions are represented as lightweight hashable objects and
    can be visualized with ``RDKitMappedReactionRenderer``.
    """

    @staticmethod
    def reactants_and_products_from_reaction(
        reaction: RDKitMappedReaction,
    ) -> tuple[tuple[RDKitSpecies, ...], tuple[RDKitSpecies, ...]]:
        reactants_side, _agents, products_side = _reaction_smiles_parts(
            reaction.mapped_reaction_smiles
        )
        reactants = tuple(
            RDKitSpecies(chunk.strip())
            for chunk in reactants_side.split(".")
            if chunk.strip()
        )
        products = tuple(
            RDKitSpecies(chunk.strip())
            for chunk in products_side.split(".")
            if chunk.strip()
        )
        return reactants, products

    @classmethod
    def from_reaction_smiles(
        cls,
        reaction_smiles: str | Iterable[str],
    ) -> "RDKitMappedReactionContainer":
        reactions = [
            RDKitMappedReaction(entry)
            for entry in _iterable_or_single(reaction_smiles)
        ]
        return cls(reactions)

    @classmethod
    def from_rdkit_reactions(
        cls,
        reactions: Iterable[Any],
    ) -> "RDKitMappedReactionContainer":
        mapped_smiles = [
            _mapped_reaction_smiles_from_rdkit_reaction(r) for r in reactions
        ]
        return cls.from_reaction_smiles(mapped_smiles)


def display_rdkit_mapped_reaction_widget(
    mapped_reaction_smiles: str | Iterable[str],
    *,
    height: str = "700px",
    width: str = "100%",
    render_options: RDKitDrawOptions | None = None,
    backend: str = "auto",
):
    """Display mapped reaction SMILES via RDKit-only images in the widget.

    Use ``render_options=RDKitDrawOptions(includeAtomMaps=False)`` to hide
    atom-map labels.
    """

    from .ipython import display_container_widget

    container = RDKitMappedReactionContainer.from_reaction_smiles(
        mapped_reaction_smiles
    )
    renderer = RDKitMappedReactionRenderer(options=render_options)
    return display_container_widget(
        container,
        view=renderer,
        height=height,
        width=width,
        backend=backend,
    )


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

    @classmethod
    def from_atom_mapped_reaction_smiles(
        cls,
        mapped_reaction_smiles: str | Iterable[str],
    ) -> CRGContainer:
        """Construct from atom-mapped reaction SMILES strings.

        Input must follow ``reactants>agents>products`` format with non-zero,
        matching atom-map numbers across reactants/products. The ``agents``
        block is currently ignored.
        """

        _require_stereomolgraph()
        reactions: list[CondensedReactionGraph] = []
        for entry in _iterable_or_single(mapped_reaction_smiles):
            reactant_graph, product_graph = _graphs_from_mapped_reaction_smiles(
                entry,
                graph_type=MolGraph,
            )
            reactions.append(
                CondensedReactionGraph.from_graphs(
                    cast(MolGraph, reactant_graph),
                    cast(MolGraph, product_graph),
                )
            )
        return cls(reactions)

    @classmethod
    def from_reaction_smiles(
        cls,
        reaction_smiles: str | Iterable[str],
    ) -> CRGContainer:
        """Build a container from mapped reaction SMILES strings.

        Expects atom mapping numbers on all reactant/product atoms.
        The ``agents`` block (middle segment in
        ``reactants>agents>products``) is currently ignored.
        """

        return cls.from_atom_mapped_reaction_smiles(reaction_smiles)

    @classmethod
    def from_rdkit_reactions(cls, reactions: Iterable[Any]) -> CRGContainer:
        """Construct from RDKit ``ChemicalReaction`` objects.

        Reactions are first serialized to reaction SMILES and then parsed as
        mapped reactant/product graphs. Any ``agents`` information is currently
        ignored.
        """

        mapped_smiles = [
            _mapped_reaction_smiles_from_rdkit_reaction(r) for r in reactions
        ]
        return cls.from_atom_mapped_reaction_smiles(mapped_smiles)


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

    @classmethod
    def from_atom_mapped_reaction_smiles(
        cls,
        mapped_reaction_smiles: str | Iterable[str],
    ) -> SCRGContainer:
        """Construct from atom-mapped reaction SMILES strings.

        Input must follow ``reactants>agents>products`` format with non-zero,
        matching atom-map numbers across reactants/products. The ``agents``
        block is currently ignored.
        """

        _require_stereomolgraph()
        reactions: list[StereoCondensedReactionGraph] = []
        for entry in _iterable_or_single(mapped_reaction_smiles):
            reactant_graph, product_graph = _graphs_from_mapped_reaction_smiles(
                entry,
                graph_type=StereoMolGraph,
            )
            reactions.append(
                StereoCondensedReactionGraph.from_graphs(
                    cast(StereoMolGraph, reactant_graph),
                    cast(StereoMolGraph, product_graph),
                )
            )
        return cls(reactions)

    @classmethod
    def from_reaction_smiles(
        cls,
        reaction_smiles: str | Iterable[str],
    ) -> SCRGContainer:
        """Build a container from mapped reaction SMILES strings.

        Expects atom mapping numbers on all reactant/product atoms.
        The ``agents`` block (middle segment in
        ``reactants>agents>products``) is currently ignored.
        """

        return cls.from_atom_mapped_reaction_smiles(reaction_smiles)

    @classmethod
    def from_rdkit_reactions(cls, reactions: Iterable[Any]) -> SCRGContainer:
        """Construct from RDKit ``ChemicalReaction`` objects.

        Reactions are first serialized to reaction SMILES and then parsed as
        mapped reactant/product graphs. Any ``agents`` information is currently
        ignored.
        """

        mapped_smiles = [
            _mapped_reaction_smiles_from_rdkit_reaction(r) for r in reactions
        ]
        return cls.from_atom_mapped_reaction_smiles(mapped_smiles)
