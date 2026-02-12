from __future__ import annotations

from pathlib import Path

from crnviewer.html import cybuilder_html, state_html
from crnviewer.ipython import CyBuilder
from crnviewer.state import cybuilder_state


def build_demo_builder() -> CyBuilder[str, str]:
    builder: CyBuilder[str, str] = CyBuilder()

    builder.add_node("CH4", label="CH4", classes=["species"])
    builder.add_node("O2", label="O2", classes=["species"])
    builder.add_node("CO2", label="CO2", classes=["species"])
    builder.add_node("H2O", label="H2O", classes=["species"])
    builder.add_node("rxn1", label="R1", classes=["reaction"])

    builder.add_edge("CH4", "rxn1")
    builder.add_edge("O2", "rxn1")
    builder.add_edge("rxn1", "CO2")
    builder.add_edge("rxn1", "H2O")

    return builder


def main() -> None:
    out_dir = Path("investigation_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    builder = build_demo_builder()

    html_direct = cybuilder_html(builder, layout="layered", layout_options={"elk.direction": "RIGHT"})
    (out_dir / "network_direct.html").write_text(html_direct, encoding="utf-8")

    state = cybuilder_state(builder, layout="layered", layout_options={"elk.direction": "RIGHT"})
    html_state = state_html(state)
    (out_dir / "network_state.html").write_text(html_state, encoding="utf-8")

    print("Wrote:")
    print(out_dir / "network_direct.html")
    print(out_dir / "network_state.html")
    print("State keys:", sorted(state.keys()))


if __name__ == "__main__":
    main()
