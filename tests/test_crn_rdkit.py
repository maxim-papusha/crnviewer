from __future__ import annotations

import pytest

ZENODO_B97D3_MAPPED_REACTIONS = (
    "[C:1]([c:2]1[n:3][o:4][n:5][n:6]1)([H:7])([H:8])[H:9]>>[C:1]1([H:7])([H:8])/[C:2](=[N:3]\\[H:9])[N:6]1[N:5]=[O:4]",
    "[C:1]([c:2]1[n:3][o:4][n:5][n:6]1)([H:7])([H:8])[H:9]>>[C:1]([C:2](=[N:3][O-:4])[N+:6]#[N:5])([H:7])([H:8])[H:9]",
    "[C:1]([c:2]1[n:3][o:4][n:5][n:6]1)([H:7])([H:8])[H:9]>>[C:1]([C:2]#[N:3])([H:7])([H:8])[H:9].[O:4]=[N+:5]=[N-:6]",
)


def test_scrg_container_from_atom_mapped_reaction_smiles() -> None:
    pytest.importorskip("rdkit")
    pytest.importorskip("stereomolgraph")

    from crnviewer.crn import SCRGContainer

    mapped = "[CH3:1].[OH:2]>>[CH3:1][OH:2]"
    container = SCRGContainer.from_atom_mapped_reaction_smiles(mapped)

    assert len(container.reactions) == 1
    reaction = next(iter(container.reactions))
    assert reaction.get_formed_bonds() == {frozenset({1, 2})}


def test_scrg_container_from_rdkit_reactions() -> None:
    pytest.importorskip("rdkit")
    pytest.importorskip("stereomolgraph")

    from rdkit.Chem import rdChemReactions

    from crnviewer.crn import SCRGContainer

    rxn = rdChemReactions.ReactionFromSmarts(
        "[CH3:1].[OH:2]>>[CH3:1][OH:2]",
        useSmiles=True,
    )

    container = SCRGContainer.from_rdkit_reactions([rxn])

    assert len(container.reactions) == 1
    reaction = next(iter(container.reactions))
    assert reaction.get_formed_bonds() == {frozenset({1, 2})}


def test_mapped_reaction_requires_atom_maps() -> None:
    pytest.importorskip("rdkit")
    pytest.importorskip("stereomolgraph")

    from crnviewer.crn import SCRGContainer

    with pytest.raises(ValueError, match="atom-map"):
        SCRGContainer.from_atom_mapped_reaction_smiles("CCO>>CCO")


def test_from_reaction_smiles_convenience_constructor() -> None:
    pytest.importorskip("rdkit")
    pytest.importorskip("stereomolgraph")

    from crnviewer.crn import SCRGContainer

    mapped = "[CH3:1].[OH:2]>>[CH3:1][OH:2]"
    container = SCRGContainer.from_reaction_smiles(mapped)

    assert len(container.reactions) == 1
    reaction = next(iter(container.reactions))
    assert reaction.get_formed_bonds() == {frozenset({1, 2})}


@pytest.mark.parametrize("mapped", ZENODO_B97D3_MAPPED_REACTIONS)
def test_zenodo_mapped_reactions_construct_scrg(mapped: str) -> None:
    pytest.importorskip("rdkit")
    pytest.importorskip("stereomolgraph")

    from crnviewer.crn import SCRGContainer

    container = SCRGContainer.from_reaction_smiles(mapped)

    assert len(container.reactions) == 1
    reaction = next(iter(container.reactions))
    assert reaction.n_atoms > 0
    assert len(container.species) >= 1
