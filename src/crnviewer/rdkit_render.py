from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class RDKitDrawOptions:
    """CRNViewer wrapper for RDKit draw options.

    Field names intentionally mirror RDKit ``MolDrawOptions`` names where
    possible, while adding ``includeAtomMaps`` as a high-level toggle.
    """

    includeAtomMaps: bool = True
    includeAtomTags: bool | None = None
    addAtomIndices: bool | None = None
    addBondIndices: bool | None = None
    baseFontSize: float | None = None
    annotationFontScale: float | None = None
    fixedBondLength: float | None = None
    highlightBondWidthMultiplier: float | None = None
    rawOptions: Mapping[str, Any] | None = None

    def apply_to(self, draw_options: Any) -> None:
        values = {
            "addAtomIndices": self.addAtomIndices,
            "addBondIndices": self.addBondIndices,
            "baseFontSize": self.baseFontSize,
            "annotationFontScale": self.annotationFontScale,
            "fixedBondLength": self.fixedBondLength,
            "highlightBondWidthMultiplier": self.highlightBondWidthMultiplier,
        }

        include_atom_tags = self.includeAtomTags
        if include_atom_tags is None and not self.includeAtomMaps:
            include_atom_tags = False
        values["includeAtomTags"] = include_atom_tags

        for name, value in values.items():
            if value is None:
                continue
            if hasattr(draw_options, name):
                setattr(draw_options, name, value)

        if self.rawOptions:
            for name, value in self.rawOptions.items():
                if hasattr(draw_options, name):
                    setattr(draw_options, name, value)


def remove_atom_maps_from_mol(mol: Any) -> Any:
    from rdkit import Chem

    copied = Chem.Mol(mol)
    for atom in copied.GetAtoms():
        atom.SetAtomMapNum(0)
    return copied


def remove_atom_maps_from_reaction(reaction: Any) -> Any:
    from rdkit.Chem import rdChemReactions

    copied = rdChemReactions.ChemicalReaction()

    for idx in range(reaction.GetNumReactantTemplates()):
        copied.AddReactantTemplate(
            remove_atom_maps_from_mol(reaction.GetReactantTemplate(idx))
        )

    for idx in range(reaction.GetNumProductTemplates()):
        copied.AddProductTemplate(
            remove_atom_maps_from_mol(reaction.GetProductTemplate(idx))
        )

    for idx in range(reaction.GetNumAgentTemplates()):
        copied.AddAgentTemplate(
            remove_atom_maps_from_mol(reaction.GetAgentTemplate(idx))
        )

    copied.Initialize()
    return copied
