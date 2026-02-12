from __future__ import annotations

from rdkit.Chem import rdChemReactions

from crnviewer.crn import CRGContainer, SCRGContainer


def summarize_container(name: str, container) -> None:
    print(f"{name}: reactions={len(container.reactions)} species={len(container.species)}")
    for idx, reaction in enumerate(container.reactions, start=1):
        formed = sorted(tuple(bond) for bond in reaction.get_formed_bonds())
        broken = sorted(tuple(bond) for bond in reaction.get_broken_bonds())
        print(f"  reaction {idx}: formed={formed}, broken={broken}")


def main() -> None:
    mapped = "[CH3:1].[OH:2]>>[CH3:1][OH:2]"

    scrg_from_smiles = SCRGContainer.from_reaction_smiles(mapped)
    summarize_container("SCRG from mapped reaction SMILES", scrg_from_smiles)

    crg_from_smiles = CRGContainer.from_reaction_smiles(mapped)
    summarize_container("CRG from mapped reaction SMILES", crg_from_smiles)

    rxn = rdChemReactions.ReactionFromSmarts(mapped, useSmiles=True)
    scrg_from_reaction = SCRGContainer.from_rdkit_reactions([rxn])
    summarize_container("SCRG from RDKit ChemicalReaction", scrg_from_reaction)


if __name__ == "__main__":
    main()
