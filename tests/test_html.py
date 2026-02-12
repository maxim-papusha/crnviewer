from __future__ import annotations

import pytest

from crnviewer.html import cybuilder_html
from crnviewer.ipython import build_builder_from_container


@pytest.fixture()
def phos_like_container():
    """Build a small SCRGContainer similar to the phos example."""

    pytest.importorskip("rdkit")
    pytest.importorskip("stereomolgraph")

    from rdkit import Chem
    from stereomolgraph import StereoCondensedReactionGraph
    from stereomolgraph.stereodescriptors import Tetrahedral

    from crnviewer.crn import SCRGContainer

    methylamine = Chem.AddHs(Chem.MolFromSmiles("NC"))
    phosgene = Chem.AddHs(Chem.MolFromSmiles("ClC(Cl)=O"))
    combined = Chem.CombineMols(methylamine, phosgene)

    scrg = StereoCondensedReactionGraph.from_rdmol(combined)
    scrg.add_formed_bond(0, 8)
    scrg.add_formed_bond(7, 2)
    scrg.add_broken_bond(7, 8)
    scrg.add_broken_bond(0, 2)
    scrg.set_atom_stereo_change(
        fleeting=Tetrahedral(atoms=(0, *scrg.bonded_to(0)))
    )
    scrg.set_atom_stereo_change(
        fleeting=Tetrahedral(atoms=(8, *scrg.bonded_to(8)))
    )

    container = SCRGContainer([scrg])
    return container


def test_cybuilder_html_supports_layered_layout(phos_like_container):
    builder = build_builder_from_container(phos_like_container)

    html = cybuilder_html(
        builder,
        layout="layered",
        layout_options={"elk.direction": "DOWN"},
    )

    assert "cytoscape.use" in html
    assert "elk" in html
    assert '"algorithm": "layered"' in html
    assert '"direction": "DOWN"' in html
    assert '"nodes":' in html and '"edges":' in html
    assert "#" in html  # contains a container id


def test_cybuilder_html_contains_download_button(phos_like_container):
    builder = build_builder_from_container(phos_like_container)

    html = cybuilder_html(builder)

    assert "download-btn" in html
    assert "Download with Positions" in html
    assert "cloneNode(true)" in html
    assert 'const layoutCfg = { name: "preset" };' in html
