import itertools
from copy import deepcopy
from collections.abc import Iterable, Sequence
from typing import Any, Callable, Hashable

import rdkit
from rdkit import Chem
from rdkit.Chem import rdFMCS
from rdkit.Chem.Draw import rdDepictor as rdDepictor
from rdkit.Chem import Draw

bond_types = {
    0: None,
    0.5: Chem.BondType.HYDROGEN,
    1: Chem.BondType.SINGLE,
    1.5: Chem.BondType.ONEANDAHALF,
    2: Chem.BondType.DOUBLE,
    2.5: Chem.BondType.TWOANDAHALF,
    3: Chem.BondType.TRIPLE,
}

inverted_bond_types = {v: k for k, v in bond_types.items()}


class AlignedRenderer:
    """Renderer that serves pre-aligned RDKit mols (with highlights) as SVG.

    Expects a mapping from graph objects to ``(Chem.Mol, highlight)`` tuples,
    where ``highlight`` carries the same fields returned by
    ``stereomolgraph.ipython.View2D._to_mol``.
    """

    def __init__(
        self,
        mol_map: dict[Hashable, tuple[Chem.Mol, Any]],
        *,
        width: int = 300,
        height: int = 300,
    ) -> None:
        self._mol_map = mol_map
        self._width = width
        self._height = height

    def svg(self, obj: Hashable) -> str:
        mol, ht = self._mol_map[obj]
        assert mol is not None
        drawer = Draw.rdMolDraw2D.MolDraw2DSVG(self._width, self._height)
        opts = drawer.drawOptions()
        opts.useBWAtomPalette()
        opts.continuousHighlight = False
        opts.highlightBondWidthMultiplier = 12
        opts.fillHighlights = False
        opts.includeRadicals = False

        drawer.DrawMolecule(
            mol,
            highlightAtoms=getattr(ht, "atoms_to_highlight", []),
            highlightAtomColors=getattr(ht, "highlight_atom_colors", {}),
            highlightBonds=getattr(ht, "bonds_to_highlight", []),
            highlightBondColors=getattr(ht, "highlight_bond_colors", {}),
        )
        drawer.FinishDrawing()
        return drawer.GetDrawingText()

def _max_spanning_tree_bfs_edges(
    distance_matrix: list[list[float]],
) -> list[tuple[int, int]]:
    # Number of nodes
    n = len(distance_matrix)

    # Initialize the maximum spanning tree with the first node
    mst_set = [0]
    mst_edges = []

    # While the maximum spanning tree does not include all nodes
    while len(mst_set) < n:
        # Find the edge with maximum weight from a node in the maximum spanning
        # tree to a node not in the tree
        max_weight = float("-inf")
        for i in mst_set:
            for j in range(n):
                if j not in mst_set and distance_matrix[i][j] > max_weight:
                    max_weight = distance_matrix[i][j]
                    max_edge = (i, j)

        # Add the found edge to the maximum spanning tree
        mst_set.append(max_edge[1])
        mst_edges.append(max_edge)

    # Use BFS to get the edges of the maximum spanning tree
    bfs_edges = []
    queue = [0]
    visited = [False] * n
    visited[0] = True
    while queue:
        i = queue.pop(0)
        for j, edge in enumerate(mst_edges):
            if edge[0] == i and not visited[edge[1]]:
                bfs_edges.append(edge)
                queue.append(edge[1])
                visited[edge[1]] = True
            elif edge[1] == i and not visited[edge[0]]:
                bfs_edges.append((edge[1], edge[0]))
                queue.append(edge[0])
                visited[edge[0]] = True

    return bfs_edges

def align_rdmol_2d(rdmol1: rdkit.Chem.Mol, rdmol2: rdkit.Chem.Mol) -> None:
    """
    Aligns the 2D coordinates of rdmol2 to rdmol1 using the maximum common
    substructure.
    :param rdmol1: rdkit.Chem.Mol
    :param rdmol2: rdkit.Chem.Mol
    """
    res = rdFMCS.FindMCS(
        mols=[rdmol1, rdmol2],
        completeRingsOnly=False,
        ringMatchesRingOnly=False,
        matchValences=False,
        matchChiralTag=False,
    )

    mcs = rdkit.Chem.MolFromSmarts(res.smartsString)
    # if deepcopy is omitted the substructure is highlighted
    atom_map = {
        a_s1: a_s2
        for a_s1, a_s2 in zip(
            deepcopy(rdmol1).GetSubstructMatch(mcs),
            deepcopy(rdmol2).GetSubstructMatch(mcs),
        )
    }
    rdDepictor.Compute2DCoords(rdmol1)

    coord_2d = {
        a_s2: rdkit.Geometry.Point2D(
            rdmol1.GetConformer().GetAtomPosition(a_s1).x,
            rdmol1.GetConformer().GetAtomPosition(a_s1).y,
        )
        for a_s1, a_s2 in atom_map.items()
    }

    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(rdmol2, coordMap=coord_2d)


def align_rdmols_2d(rdmols: Sequence[rdkit.Chem.Mol]) -> None:
    """
    Aligns the 2D coordinates of all rdmols to the first rdmol in the iterable.
    :param rdmols: Sequence[rdkit.Chem.Mol]
    """
    # Precompute explicit valence so MCS matching with valence constraints
    # does not throw when valence information is missing.
    for mol in rdmols:
        mol.UpdatePropertyCache(strict=False)

    sim_mat = [
        [
            rdkit.Chem.MolFromSmarts(
                rdFMCS.FindMCS(
                    mols=[rdmol1, rdmol2],
                    completeRingsOnly=False,
                    ringMatchesRingOnly=False,
                    matchValences=False,
                    matchChiralTag=False,
                ).smartsString
            ).GetNumAtoms()
            for (i, rdmol1) in enumerate(rdmols)
        ]
        for (j, rdmol2) in enumerate(rdmols)
    ]

    for i1, i2 in _max_spanning_tree_bfs_edges(sim_mat):
        align_rdmol_2d(rdmols[i1], rdmols[i2])


def aligned_renderer_from_container(
    container: Any,
    *,
    label_func: Callable[[Hashable], str] | None = None,
    align_reactions: bool = False,
    view_factory: Callable[[], Any] | None = None,
) -> AlignedRenderer:
    """Build an ``AlignedRenderer`` with pre-aligned RDKit mols for a container.

    Species (and optionally reaction) graphs are converted to RDKit mols using
    ``stereomolgraph.ipython.View2D._to_mol`` to preserve existing highlight
    metadata, then aligned via maximum common substructure. Coordinates are
    *not* recomputed during rendering, so the resulting SVGs share a consistent
    frame.
    """

    try:
        from stereomolgraph.ipython import View2D  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("View2D is required to build aligned renderers") from exc

    view = view_factory() if view_factory is not None else View2D()

    mol_map: dict[Hashable, tuple[Chem.Mol, Any]] = {}
    mols_to_align: list[Chem.Mol] = []

    # Collect species mols first (these anchor alignment order)
    for species in container.species:
        mol, ht = view._to_mol(species)  # type: ignore[attr-defined]
        mol_map[species] = (mol, ht)
        mols_to_align.append(mol)

    if align_reactions:
        for reaction in container.reactions:
            mol, ht = view._to_mol(reaction)  # type: ignore[attr-defined]
            mol_map[reaction] = (mol, ht)
            mols_to_align.append(mol)

    if len(mols_to_align) >= 2:
        align_rdmols_2d(mols_to_align)

    return AlignedRenderer(mol_map, width=view.width, height=view.height)


def display_aligned_container(
    container: Any,
    *,
    label_func: Callable[[Hashable], str] | None = None,
    align_reactions: bool = False,
    skip_species: Iterable[Hashable] | None = None,
    skip_reactions: Iterable[Hashable] | None = None,
    height: str = "700px",
    width: str = "100%",
):
    """Display a container with aligned SVG node images.

    Alignment reuses existing highlight metadata (formed/broken bonds, etc.).
    When ``align_reactions`` is True, reaction nodes are included in the
    alignment alongside species.
    """

    from .ipython import display_container_widget

    renderer = aligned_renderer_from_container(
        container,
        label_func=label_func,
        align_reactions=align_reactions,
    )

    return display_container_widget(
        container,
        view=renderer,
        label_func=label_func,
        skip_species=skip_species,
        skip_reactions=skip_reactions,
        height=height,
        width=width,
    )


def _rdcrg_from_mols(
    reactants: Sequence[rdkit.Chem.Mol], products: Sequence[rdkit.Chem.Mol]
) -> rdkit.Chem.Mol:
    mol1 = reactants
    mol2 = products

    crg = Chem.RWMol()

    assert (n_atoms := mol1.GetNumAtoms()) == mol2.GetNumAtoms()

    map_num_idx_dict1 = {
        a.GetAtomMapNum(): a.GetIdx() for a in mol1.GetAtoms()
    }
    map_num_idx_dict2 = {
        a.GetAtomMapNum(): a.GetIdx() for a in mol2.GetAtoms()
    }

    idx_map_num_dict1 = {v: k for k, v in map_num_idx_dict1.items()}
    idx_map_num_dict2 = {v: k for k, v in map_num_idx_dict2.items()}

    for map_num in set(map_num_idx_dict1.keys()) | set(
        map_num_idx_dict2.keys()
    ):
        idx1 = map_num_idx_dict1[map_num]
        idx2 = map_num_idx_dict2[map_num]
        a1, a2 = mol1.GetAtomWithIdx(idx1), mol2.GetAtomWithIdx(idx2)

        if a1.GetSymbol() == a2.GetSymbol():
            a = Chem.Atom(a1.GetSymbol())
        else:
            raise ValueError("Wrong atom labeling")

        if a1.GetFormalCharge() == a2.GetFormalCharge():
            a.SetFormalCharge(a1.GetFormalCharge())
        if a1.GetNumRadicalElectrons() == a2.GetNumRadicalElectrons():
            a.SetNumRadicalElectrons(a1.GetNumRadicalElectrons())
        if a1.GetIsotope() == a2.GetIsotope():
            a.SetIsotope(a1.GetIsotope())
        a.SetAtomMapNum(map_num)
        crg.AddAtom(a)
        del a

    map_num_idx_dict = {a.GetAtomMapNum(): a.GetIdx() for a in crg.GetAtoms()}

    atom_pairs = tuple(itertools.combinations(range(n_atoms), 2))

    for idx_bond_atoms1, idx_bond_atoms2 in itertools.product(
        atom_pairs, atom_pairs
    ):
        b1 = mol1.GetBondBetweenAtoms(*idx_bond_atoms1)
        b2 = mol2.GetBondBetweenAtoms(*idx_bond_atoms2)

        map_num_set1 = {idx_map_num_dict1[atom] for atom in idx_bond_atoms1}
        map_num_set2 = {idx_map_num_dict2[atom] for atom in idx_bond_atoms2}

        if map_num_set1 == map_num_set2:
            bond_order1 = inverted_bond_types.get(
                None if b1 is None else b1.GetBondType()
            )
            bond_order2 = inverted_bond_types.get(
                None if b2 is None else b2.GetBondType()
            )
            if bond_order1 is None or bond_order2 is None:
                continue
            
            crg_bond_idxs = {
                map_num_idx_dict[atom_map_num] for atom_map_num in map_num_set1
            }
            crg_bond_idxs2 = {
                map_num_idx_dict[atom_map_num] for atom_map_num in map_num_set2
            }

            assert crg_bond_idxs == crg_bond_idxs2 and {
                mol1.GetAtomWithIdx(idx).GetSymbol() for idx in idx_bond_atoms1
            } == {
                mol2.GetAtomWithIdx(idx).GetSymbol() for idx in idx_bond_atoms2
            }

            if bond_order1 == 0 and bond_order2 == 0:
                pass
            elif bond_order1 == bond_order2:
                crg.AddBond(*crg_bond_idxs, order=bond_types[bond_order1])
            elif bond_order1 == 0 or bond_order2 == 0:
                crg.AddBond(*crg_bond_idxs, order=bond_types[0.5])
            else:
                new_bond_order = round((bond_order1 + bond_order2) / 2, 1)

                if not round(new_bond_order % 0.5, 1) == 0:
                    new_bond_order = round(new_bond_order, 0)

                crg.AddBond(*crg_bond_idxs, bond_types[new_bond_order])

    for a in crg.GetAtoms():
        a.SetNoImplicit(True)
        # a.SetAtomMapNum(0)
    return rdkit.Chem.Mol(crg)


def _rdcrg_from_mapped_reaction_smiles(
    atom_mapped_reaction_smiles,
) -> rdkit.Chem.Mol:
    smiles1, _, smiles2 = atom_mapped_reaction_smiles.split(">")
    mol1 = Chem.MolFromSmiles(smiles1.strip(), sanitize=False)
    mol2 = Chem.MolFromSmiles(smiles2.strip(), sanitize=False)
    return _rdcrg_from_mols(mol1, mol2)

def from_mapped_reaction_smiles(
    mapped_reaction_smiles: str,
    atom_map_num: bool = True,
) -> tuple[rdkit.Chem.Mol, rdkit.Chem.Mol, rdkit.Chem.Mol]:
    """
    Converts an atom-mapped reaction SMILES string to a rdmol representing 
    the condensed reaction graph.
    returns a tuple of reactants, crg and products.
    """
    smiles1, _, smiles2 = mapped_reaction_smiles.split(">")
    mol1 = Chem.MolFromSmiles(smiles1.strip(), sanitize=False)
    mol2 = Chem.MolFromSmiles(smiles2.strip(), sanitize=False)
    crg_mol = _rdcrg_from_mols(mol1, mol2)
    if not atom_map_num:
        for a in crg_mol.GetAtoms():
            a.SetAtomMapNum(0)
        for a in mol1.GetAtoms():
            a.SetAtomMapNum(0)
        for a in mol2.GetAtoms():
            a.SetAtomMapNum(0)
    return mol1, crg_mol, mol2