"""
train_cfc_landscape.py — Train a CfC Liquid Neural Network to dynamically
modulate landscape parameters (sigma_polarization, attractor/repeller strengths,
and positions) reactively based on polarization and Gini context.

## Objective
The energy landscape governs the "physics" of opinion flow. By modulating it:
- High polarization + high Gini → deepen faction wells (increase attractor strength).
- Low polarization → increase diffusion (sigma_p) to encourage exploration.
- High volatility → lower barriers (decrease repeller strength) to allow opinion flow.
- Attractor positions shift toward the current mean opinion of the system.

## Data Generation Strategy
Generate synthetic trajectories using the Energy Engine. For each state, we
define the "ideal" landscape parameters that would drive the system toward
stable, realistic dynamics based on the described physical intuitions.

## Architecture
    CfCCell(input_dim=5, hidden_size=32) → Linear(5) → Constraints

Input features (5):
    [polarization_t,          # current polarization index
     delta_pol_t1,            # polarization velocity (1-step)
     delta_pol_t5,            # polarization velocity (5-step window)
     gini_coefficient,        # socioeconomic inequality
     volatility_index]        # std of recent opinion changes

Targets (5):
    [sigma_p,                 # Diffusion: Softplus -> [0, 1]
     attractor_strength,       # Strength: Softplus
     repeller_strength,        # Strength: Softplus
     attractor_pos,           # Position: Tanh -> [-1, 1]
     repeller_pos]            # Position: Tanh -> [-1, 1]
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)
CALIBRATED_DIR = MODELS_DIR / "cfc_calibrated"
CALIBRATED_DIR.mkdir(exist_ok=True)


def generate_landscape_training_data(n_trajectories: int = 1000, seed: int = 42) -> dict:
    """Generate synthetic trajectories and target landscape parameters.

    Args:
        n_trajectories: Number of synthetic trajectories to generate.
        seed: RNG seed.

    Returns:
        Dict with 'X' (features) and 'y' (target landscape parameters).
    """
    import importlib.util

    if importlib.util.find_spec("torch") is None:
        raise ImportError("PyTorch is required for training: pip install torch>=2.2.0")

    from energy_engine import SocialEnergyEngine, random_network

    rng = np.random.default_rng(seed)
    N_agents = 50
    steps = 365
    connectivity = 0.3

    X_list = []
    y_list = []

    for i in range(n_trajectories):
        # Baseline parameters for this trajectory
        gini = float(rng.uniform(0.15, 0.65))
        temperature = float(rng.uniform(0.01, 0.20))

        eng = SocialEnergyEngine(
            range_type="bipolar",
            temperature=temperature,
            lambda_social=0.5,  # fixed for landscape training
            gini_coefficient=gini,
            seed=42 + i,
        )

        adj = random_network(N_agents, connectivity=connectivity, seed=42 + i)
        opinions = rng.uniform(-0.5, 0.5, N_agents)

        # Initial landscape
        attractors = [{"position": 0.8, "strength": 1.0}, {"position": -0.8, "strength": 1.0}]
        repellers = [{"position": 0.0, "strength": 0.5}]

        pol_history = []
        mean_op_history = []

        # Simulate to get realistic trajectories
        for _ in range(steps):
            opinions = eng.step(opinions, adj, attractors, repellers, eta=0.01)
            pol = float(np.std(opinions) / 1.0)
            pol_history.append(pol)
            mean_op_history.append(float(np.mean(opinions)))

        pol_arr = np.array(pol_history)
        mean_op_arr = np.array(mean_op_history)

        for t in range(6, len(pol_arr) - 1):
            pol_t = pol_arr[t]
            delta_t1 = pol_arr[t] - pol_arr[t - 1]
            delta_t5 = pol_arr[t] - pol_arr[t - 5] if t >= 5 else 0.0
            volatility = float(
                np.std([pol_arr[t - j] - pol_arr[t - j - 1] for j in range(1, 4)])
                if t >= 3
                else 0.0
            )

            # TARGET GENERATION (Physical Intuition)
            # 1. sigma_p: Low polarization -> increase diffusion to explore
            sigma_p = 0.1 + (1.0 - pol_t) * 0.4

            # 2. Attractor Strength: High polarization + High Gini -> deepen wells
            attr_strength = 1.0 + (pol_t * gini * 2.0)

            # 3. Repeller Strength: High volatility -> decrease barriers
            rep_strength = 0.5 / (1.0 + volatility * 10.0)

            # 4. Attractor Position: Shift toward current mean opinion
            # Basic logic: one attractor follows mean, other stays opposite
            mean_op = mean_op_arr[t]
            attr_pos = np.clip(mean_op, -1.0, 1.0)

            # 5. Repeller Position: Usually opposite to the dominant shift
            rep_pos = np.clip(-mean_op, -1.0, 1.0)

            features = [pol_t, delta_t1, delta_t5, gini, volatility]
            targets = [sigma_p, attr_strength, rep_strength, attr_pos, rep_pos]

            X_list.append(features)
            y_list.append(targets)

    return {"X": np.array(X_list, dtype=np.float32), "y": np.array(y_list, dtype=np.float32)}


def train_landscape_corrector(
    dataset: dict,
    hidden_size: int = 32,
    epochs: int = 50,
    lr: float = 3e-4,
    dt: float = 0.1,
) -> str:
    """Train the CfC landscape modulator.

    Args:
        dataset: Dict with 'X' (features) and 'y' (target parameters).
        hidden_size: Hidden state dimension.
        epochs: Number of training epochs.
        lr: Learning rate.
        dt: ODE integration step.

    Returns:
        Path to saved model.
    """
    import torch
    import torch.nn as nn

    from cfc_engine import CfCCell

    X = torch.tensor(dataset["X"], dtype=torch.float32)
    y = torch.tensor(dataset["y"], dtype=torch.float32)

    input_dim = X.shape[1]
    cell = CfCCell(input_dim, hidden_size)
    readout = nn.Linear(hidden_size, 5)

    optimizer = torch.optim.Adam(list(cell.parameters()) + list(readout.parameters()), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.5, patience=10)
    criterion = nn.MSELoss()

    # Split 80/10/10
    n = len(X)
    idx = np.random.default_rng(42).permutation(n)
    n_train = int(0.8 * n)
    n_val = int(0.1 * n)
    train_idx = idx[:n_train]
    val_idx = idx[n_train : n_train + n_val]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    best_val_loss = float("inf")
    patience = 15
    patience_counter = 0
    training_log = {"epochs": [], "train_loss": [], "val_loss": []}

    log.info(f"[CfC Landscape] Starting training: {n_train} train, {n_val} val samples")

    BATCH_SIZE = 1024

    for epoch in range(epochs):
        cell.train()
        readout.train()
        epoch_loss = 0.0
        n_batches = 0
        perm = np.random.default_rng(42 + epoch).permutation(len(X_train))

        for batch_start in range(0, len(X_train), BATCH_SIZE):
            batch_idx = perm[batch_start : batch_start + BATCH_SIZE]
            X_batch = X_train[batch_idx]
            y_batch = y_train[batch_idx]

            optimizer.zero_grad()
            h = torch.zeros(len(X_batch), hidden_size)
            h = cell(h, X_batch, dt=dt)

            # Apply constraints to output
            raw_out = readout(h)
            # [sigma_p, attr_s, rep_s, attr_p, rep_p]
            # index 0,1,2 -> Softplus; index 3,4 -> Tanh
            pred = torch.cat(
                [torch.nn.functional.softplus(raw_out[:, :3]), torch.tanh(raw_out[:, 3:])], dim=1
            )

            # Bound sigma_p to [0, 1]
            pred_bounded = pred.clone()
            pred_bounded[:, 0] = torch.clamp(pred[:, 0], 0.0, 1.0)

            loss = criterion(pred_bounded, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(cell.parameters()) + list(readout.parameters()), 1.0
            )
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / n_batches

        cell.eval()
        readout.eval()
        with torch.no_grad():
            h_val = torch.zeros(len(X_val), hidden_size)
            h_val = cell(h_val, X_val, dt=dt)
            raw_val = readout(h_val)
            val_pred = torch.cat(
                [torch.nn.functional.softplus(raw_val[:, :3]), torch.tanh(raw_val[:, 3:])], dim=1
            )
            val_pred[:, 0] = torch.clamp(val_pred[:, 0], 0.0, 1.0)
            val_loss = criterion(val_pred, y_val).item()

        scheduler.step(val_loss)
        training_log["epochs"].append(epoch)
        training_log["train_loss"].append(train_loss)
        training_log["val_loss"].append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            model_path = CALIBRATED_DIR / "cfc_landscape.pt"
            torch.save(
                {"cell_state": cell.state_dict(), "readout_state": readout.state_dict()},
                model_path,
            )
        else:
            patience_counter += 1

        if epoch % 10 == 0 or epoch == epochs - 1:
            log.info(
                f"  Epoch {epoch}/{epochs}: train_loss={train_loss:.6f}, val_loss={val_loss:.6f}"
            )

        if patience_counter >= patience:
            log.info(f"  Early stopping at epoch {epoch}")
            break

    config = {
        "model_name": "CfCLandscapeModulator-N5H32",
        "input_features": ["polarization_t", "delta_pol_t1", "delta_pol_t5", "gini", "volatility"],
        "targets": [
            "sigma_p",
            "attractor_strength",
            "repeller_strength",
            "attractor_pos",
            "repeller_pos",
        ],
        "hidden_size": hidden_size,
        "epochs_run": len(training_log["epochs"]),
        "best_val_loss": best_val_loss,
        "architecture": "CfCCell(ODE) + Linear readout + Mixed Activations",
    }
    (CALIBRATED_DIR / "cfc_landscape_config.json").write_text(json.dumps(config, indent=2))
    (CALIBRATED_DIR / "cfc_landscape_training_log.json").write_text(
        json.dumps(training_log, indent=2)
    )

    log.info(f"[CfC Landscape] Training complete. Best val loss: {best_val_loss:.6f}")
    return str(model_path)


def main():
    """Main pipeline execution."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    log.info("=== Step 1: Generating landscape training data ===")
    t0 = time.time()
    dataset = generate_landscape_training_data(n_trajectories=1000, seed=42)
    log.info(f"Data generation complete in {time.time() - t0:.1f}s")
    log.info(f"  Samples: {len(dataset['X'])}, Features: {dataset['X'].shape[1]}")

    log.info("=== Step 2: Training CfC Landscape Modulator ===")
    t0 = time.time()
    model_path = train_landscape_corrector(dataset, hidden_size=32, epochs=20, lr=3e-4)
    log.info(f"Training complete in {time.time() - t0:.1f}s")

    log.info("=== Step 3: Prediction smoke test ===")
    import torch
    import torch.nn as nn

    from cfc_engine import CfCCell

    checkpoint = torch.load(model_path)
    cell = CfCCell(5, 32)
    cell.load_state_dict(checkpoint["cell_state"])
    readout = nn.Linear(32, 5)
    readout.load_state_dict(checkpoint["readout_state"])

    test_input = torch.randn(1, 5)
    cell.eval()
    readout.eval()
    with torch.no_grad():
        h = torch.zeros(1, 32)
        h = cell(h, test_input, dt=0.1)
        out = readout(h)
        # Apply the same constraints
        pred = torch.cat([torch.nn.functional.softplus(out[:, :3]), torch.tanh(out[:, 3:])], dim=1)
        pred[:, 0] = torch.clamp(pred[:, 0], 0.0, 1.0)
        log.info(f"Smoke test prediction: {pred.numpy()[0]}")

    return model_path


if __name__ == "__main__":
    main()
