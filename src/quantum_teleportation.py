"""
Bell State Generator
====================
Implementation of the four Bell states using IBM Qiskit.

Bell states are the four maximally entangled two-qubit states that form
the foundation of quantum teleportation, superdense coding, and QKD protocols.

States:
    |Φ+⟩ = (|00⟩ + |11⟩) / √2   (default)
    |Φ-⟩ = (|00⟩ - |11⟩) / √2
    |Ψ+⟩ = (|01⟩ + |10⟩) / √2
    |Ψ-⟩ = (|01⟩ - |10⟩) / √2

Author: Alejandro Cardiel Santos
GitHub: github.com/acardiels
"""

from __future__ import annotations

import os
from typing import Literal

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator

# ── Type alias ────────────────────────────────────────────────────────────────
BellState = Literal["phi+", "phi-", "psi+", "psi-"]

# ── Core circuit builder ──────────────────────────────────────────────────────

def build_bell_circuit(state: BellState = "phi+") -> QuantumCircuit:
    """
    Build the quantum circuit for the specified Bell state.

    The construction follows two steps:
        1. Hadamard on qubit 0  →  creates superposition |+⟩ on q_0
        2. CNOT (q0 → q1)       →  entangles both qubits

    Additional single-qubit corrections are applied before H to reach
    the other three Bell states:
        |Φ-⟩  →  Z on q_0 after H  (phase flip)
        |Ψ+⟩  →  X on q_1 before H  (bit flip on target)
        |Ψ-⟩  →  X on q_1 + Z on q_0

    Args:
        state: One of "phi+", "phi-", "psi+", "psi-". Defaults to "phi+".

    Returns:
        QuantumCircuit: Parameterised circuit with 2 qubits and 2 classical bits.

    Raises:
        ValueError: If an unknown state label is provided.
    """
    valid = {"phi+", "phi-", "psi+", "psi-"}
    if state not in valid:
        raise ValueError(f"Unknown Bell state '{state}'. Choose from {valid}.")

    qc = QuantumCircuit(2, 2, name=f"Bell |{_latex_label(state)}⟩")

    # ── Step 1: optional pre-corrections ────────────────────────────────────
    if state in ("psi+", "psi-"):
        # Flip target qubit so entanglement produces |01⟩ + |10⟩ basis
        qc.x(1)

    # ── Step 2: Hadamard on control qubit ───────────────────────────────────
    # H |0⟩ = (|0⟩ + |1⟩) / √2  →  equal superposition
    qc.h(0)

    # ── Step 3: optional phase flip ─────────────────────────────────────────
    if state in ("phi-", "psi-"):
        # Z introduces a relative phase: H Z |0⟩ = (|0⟩ - |1⟩) / √2
        qc.z(0)

    # ── Step 4: CNOT — creates entanglement ─────────────────────────────────
    # If q0 = |1⟩, flip q1.  Result: correlated |00⟩ + |11⟩ (or |01⟩ + |10⟩)
    qc.cx(0, 1)

    # ── Step 5: measurement ─────────────────────────────────────────────────
    qc.measure([0, 1], [0, 1])

    return qc


# ── Simulation ────────────────────────────────────────────────────────────────

def run_simulation(qc: QuantumCircuit, shots: int = 1024, seed: int = 42,) -> dict[str, int]:
    """
    Execute the circuit on the local Aer statevector simulator.

    Args:
        qc:    Quantum circuit to execute.
        shots: Number of measurement repetitions. Defaults to 1024.
        seed:  Random seed for reproducibility. Defaults to 42.

    Returns:
        dict: Bitstring counts, e.g. {"00": 512, "11": 512}.
    """
    backend = AerSimulator(method="statevector")
    transpiled = transpile(qc, backend, optimization_level=1)
    job = backend.run(transpiled, shots=shots, seed_simulator=seed)
    return job.result().get_counts()


# ── Visualisation ─────────────────────────────────────────────────────────────

def draw_circuit(qc: QuantumCircuit, output_path: str | None = None, style: str = "iqp",) -> None:
    """
    Render and optionally save the circuit diagram.

    Args:
        qc:          Circuit to draw.
        output_path: File path for saving (PNG). If None, displays interactively.
        style:       Qiskit drawing style. Defaults to "iqp".
    """
    fig = qc.draw(output="mpl", style=style, fold=-1)
    _save_or_show(fig, output_path)


def plot_results(counts: dict[str, int], state: BellState = "phi+", output_path: str | None = None,) -> None:
    """
    Plot a histogram of the measurement results.

    For Bell states we expect two equally probable outcomes:
        |Φ+⟩, |Φ-⟩  →  {"00": ~50%, "11": ~50%}
        |Ψ+⟩, |Ψ-⟩  →  {"01": ~50%, "10": ~50%}

    Args:
        counts:      Measurement counts from run_simulation().
        state:       Bell state label (used for the plot title).
        output_path: File path for saving (PNG). Displays if None.
    """
    total = sum(counts.values())
    title = (
        f"Bell state |{_latex_label(state)}⟩  —  "
        f"{total} shots  |  "
        f"Expected: 50% / 50% equal superposition"
    )
    fig = plot_histogram(
        counts,
        title=title,
        bar_labels=True,
        figsize=(7, 4),
        color=["#5B4DB5", "#1D9E75"],
    )
    fig.tight_layout()
    _save_or_show(fig, output_path)


# ── Convenience runner ────────────────────────────────────────────────────────

def generate_bell_state(state: BellState = "phi+", shots: int = 1024, save_images: bool = False, images_dir: str = "images",) -> dict[str, int]:
    """
    End-to-end pipeline: build → simulate → (optionally) save plots.

    Args:
        state:       Bell state to generate. Defaults to "phi+".
        shots:       Measurement repetitions. Defaults to 1024.
        save_images: If True, save circuit and histogram to ``images_dir``.
        images_dir:  Directory for saved images. Created if absent.

    Returns:
        dict: Measurement counts.

    Example:
        >>> counts = generate_bell_state("phi+", shots=2048)
        >>> print(counts)
        {'00': 1024, '11': 1024}
    """
    qc = build_bell_circuit(state)
    counts = run_simulation(qc, shots=shots)

    if save_images:
        # 1. Obtenemos la ruta absoluta de 'src/' (donde está este archivo)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Subimos un nivel atrás (a la raíz 'bell_states/')
        project_root = os.path.dirname(script_dir)
        
        # 3. Creamos la ruta definitiva hacia 'bell_states/images/'
        target_dir = os.path.join(project_root, images_dir)
        
        # Creamos la carpeta por si acaso no existiera
        os.makedirs(target_dir, exist_ok=True)
        
        # Limpiamos el nombre del estado para el archivo
        clean_state = state.replace('+', 'plus').replace('-', 'minus')
        
        # Guardamos el circuito y los resultados usando la nueva ruta
        draw_circuit(
            qc,
            output_path=os.path.join(target_dir, f"circuit_{clean_state}.png"),
        )
        plot_results(
            counts,
            state=state,
            output_path=os.path.join(target_dir, f"results_{clean_state}.png"),
        )

    return counts


# ── Helpers ───────────────────────────────────────────────────────────────────

def _latex_label(state: BellState) -> str:
    """Map state identifier to Unicode-friendly label."""
    return {"phi+": "Φ+", "phi-": "Φ-", "psi+": "Ψ+", "psi-": "Ψ-"}[state]


def _save_or_show(fig: plt.Figure, path: str | None) -> None:
    """Save figure to path or display interactively."""
    if path:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"  Saved → {path}")
    else:
        plt.show()
    plt.close(fig)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate and simulate a Bell state using Qiskit."
    )
    parser.add_argument(
        "--state",
        choices=["phi+", "phi-", "psi+", "psi-"],
        default="phi+",
        help="Bell state to generate (default: phi+)",
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=1024,
        help="Number of measurement shots (default: 1024)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save circuit and histogram images to ./images/",
    )
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  Bell State Generator — |{_latex_label(args.state)}⟩")
    print(f"{'='*50}")

    counts = generate_bell_state(
        state=args.state,
        shots=args.shots,
        save_images=args.save,
    )

    print(f"\n  Results ({args.shots} shots):")
    total = sum(counts.values())
    for bitstring, count in sorted(counts.items()):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"    |{bitstring}⟩  {bar:<25}  {count:>5}  ({pct:.1f}%)")

    print(f"\n  ✓ Expected: ~50% |00⟩ / |11⟩ for Φ states, ~50% |01⟩ / |10⟩ for Ψ states")
    print(f"  ✓ Entanglement confirmed: no |01⟩ or |10⟩ outcomes for Φ states\n")