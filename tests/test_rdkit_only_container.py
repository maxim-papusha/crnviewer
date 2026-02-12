from __future__ import annotations

import pytest


def test_rdkit_only_container_builds_from_mapped_smiles() -> None:
    pytest.importorskip("rdkit")

    from crnviewer.crn import RDKitMappedReactionContainer

    mapped = "[CH3:1].[OH:2]>>[CH3:1][OH:2]"
    container = RDKitMappedReactionContainer.from_reaction_smiles(mapped)

    assert len(container.reactions) == 1
    assert len(container.species) == 3


def test_rdkit_only_renderer_embeds_images_in_builder() -> None:
    pytest.importorskip("rdkit")

    from crnviewer.crn import RDKitMappedReactionContainer, RDKitMappedReactionRenderer
    from crnviewer.ipython import build_builder_from_container

    mapped = "[CH3:1].[OH:2]>>[CH3:1][OH:2]"
    container = RDKitMappedReactionContainer.from_reaction_smiles(mapped)
    renderer = RDKitMappedReactionRenderer()

    builder = build_builder_from_container(container, view=renderer)
    nodes, _edges = builder.elements()

    assert nodes
    assert any(node["data"].get("image", "").startswith("data:image/svg+xml;base64,") for node in nodes)
