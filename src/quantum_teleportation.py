"""
Quantum Teleportation — Bell State/ EPR State |Φ+⟩ = (|00⟩ + |11⟩) / √2   (default)
====================
Implementation of the quantum teleportation protocol using IBM Qiskit.

Author: Alejandro Cardiel Santos
GitHub: github.com/acardiels
"""

from __future__ import annotations

import os
from typing import Literal

import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator
from qiskit import QuantumCircuit, transpile, QuantumRegister, ClassicalRegister
from qiskit.quantum_info import random_statevector, Statevector, partial_trace, state_fidelity


# ── Type alias ────────────────────────────────────────────────────────────────
BellState = Literal["phi+"]

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
        state: "phi+".

    Returns:
        QuantumCircuit: Parameterised circuit with 2 qubits and 2 classical bits.

    Raises:
        ValueError: If an unknown state label is provided.
    """
    valid = {"phi+"}
    if state not in valid:
        raise ValueError(f"Unknown Bell state '{state}'. Choose from {valid}.")

    qc = QuantumCircuit(2)

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


    return qc

# --- Quantum Teleportation Circuit Builder ---

def build_quantum_teleportation_circuit(epr_state: BellState = "phi+", quantum_state) -> QuantumCircuit:
    """
        Build the quantum circuit for the Quantum Teleportation protocol.
    
        The construction follows two steps:
            1. Bell state preparation (q1 and q2)  →  creates entangled pair
            2. CNOT (q0 → q1)       →  entangles both qubits
            3. Hadamard on qubit 0  →  creates superposition |+⟩ on q_0
            4. Measurement of q0 and q1  →  collapses the state of q2 to the teleported state
    
        Args:
            state: Bell state "phi+" as EPR state.
            quantum_state: The quantum state to be teleported.
    
        Returns:
            QuantumCircuit: Parameterised circuit with 3 qubits and 2 classical bits.
    
        Raises:
            ValueError: If an unknown Bell state "phi+" label is provided.
    """

    valid = {"phi+"}

    if epr_state not in valid:
            raise ValueError(f"Invalid EPR state '{epr_state}'. Choose from {valid}.")

    qr = QuantumRegister(3, name="q")
    cr = ClassicalRegister(2, name="c")    
    qc_quantum_teleportation = QuantumCircuit(qr, cr, name="Quantum Teleportation for State Ψ")

    qc_quantum_teleportation.initialize(quantum_state, 0)

    qc_quantum_teleportation.append(build_bell_circuit(epr_state), [1, 2])

    qc_quantum_teleportation.cx(0, 1)

    qc_quantum_teleportation.h(0)

    qc_quantum_teleportation.measure([0, 1], [0, 1])

    # If bit 0 is 1 (c[0] == 1) -> Apply Z gate
    with qc_quantum_teleportation.if_test((cr[0], 1)):
        qc_quantum_teleportation.z(qr[2])

    # If bit 1 is 1 (c[1] == 1) -> Apply X gate
    with qc_quantum_teleportation.if_test((cr[1], 1)):
        qc_quantum_teleportation.x(qr[2])

    return qc_quantum_teleportation



# ── Simulation ────────────────────────────────────────────────────────────────

def run_simulation(qc: QuantumCircuit) -> dict[str, int]:
    """
    Execute the circuit on the local Aer statevector simulator.

    Args:
        qc:    Quantum circuit to execute.

    Returns:
        dict: Bitstring counts, e.g. {"00": 512, "11": 512}.
    """
    backend = AerSimulator(method="statevector")
    qc_sim = build_quantum_teleportation_circuit(epr_state="phi+", quantum_state=quantum_state)
    qc_sim.save_density_matrix()  

    transpiled = transpile(qc_sim, backend, optimization_level=1)
    result = backend.run(transpiled).result()

    rho_total = result.data()["density_matrix"]

    rho_bob = partial_trace(rho_total, [0, 1])

    state_alice = Statevector(quantum_state)

    fidelity = state_fidelity(state_alice, rho_bob)

    return result.get_counts(), fidelity


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

    quantum_state = random_statevector(2, seed=42) 

    parser = argparse.ArgumentParser(
        description="Generate and simulate Quantum Teleportation using Qiskit."
    )
    parser.add_argument(
        "--state",
        choices=["phi+"],
        default="phi+",
        help="Bell state/ EPR state (phi+)",
    )
    
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  Bell State Generator — |{_latex_label(args.state)}⟩")
    print(f"{'='*50}")

    print(f"\n{'='*50}")
    print(f"  Quantum State Ψ — {quantum_state}")
    print(f"{'='*50}")

    counts = generate_quantum_teleportation(
        state=args.state, quantum_state=quantum_state
    )

    print(f"\n  Results ({args.shots} shots):")
    total = sum(counts.values())
    for bitstring, count in sorted(counts.items()):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"    |{bitstring}⟩  {bar:<25}  {count:>5}  ({pct:.1f}%)")

    print(f"\n  ✓ Expected: ~50% |00⟩ / |11⟩ for Φ states, ~50% |01⟩ / |10⟩ for Ψ states")
    print(f"  ✓ Entanglement confirmed: no |01⟩ or |10⟩ outcomes for Φ states\n")