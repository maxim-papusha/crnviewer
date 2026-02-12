from __future__ import annotations

import pytest


def test_remove_atom_maps_from_mol() -> None:
    pytest.importorskip("rdkit")

    from rdkit import Chem

    from crnviewer.rdkit_render import remove_atom_maps_from_mol

    mol = Chem.MolFromSmiles("[CH3:1][OH:2]", sanitize=False)
    assert mol is not None
    assert any(atom.GetAtomMapNum() > 0 for atom in mol.GetAtoms())

    cleared = remove_atom_maps_from_mol(mol)
    assert all(atom.GetAtomMapNum() == 0 for atom in cleared.GetAtoms())


def test_remove_atom_maps_from_reaction() -> None:
    pytest.importorskip("rdkit")

    from rdkit.Chem import rdChemReactions

    from crnviewer.rdkit_render import remove_atom_maps_from_reaction

    rxn = rdChemReactions.ReactionFromSmarts(
        "[CH3:1].[OH:2]>>[CH3:1][OH:2]",
        useSmiles=True,
    )
    assert rxn is not None

    cleared = remove_atom_maps_from_reaction(rxn)
    reactant = cleared.GetReactantTemplate(0)
    product = cleared.GetProductTemplate(0)

    assert all(atom.GetAtomMapNum() == 0 for atom in reactant.GetAtoms())
    assert all(atom.GetAtomMapNum() == 0 for atom in product.GetAtoms())


def test_renderer_supports_hiding_atom_maps() -> None:
    pytest.importorskip("rdkit")

    from crnviewer.crn import RDKitMappedReactionRenderer, RDKitSpecies
    from crnviewer.rdkit_render import RDKitDrawOptions

    renderer = RDKitMappedReactionRenderer(
        options=RDKitDrawOptions(includeAtomMaps=False)
    )
    svg = renderer.svg(RDKitSpecies("[CH3:1][OH:2]"))

    assert svg.startswith("<?xml")
