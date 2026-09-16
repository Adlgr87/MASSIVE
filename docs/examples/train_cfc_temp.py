"""
train_cfc_temp.py — Train a CfC Liquid Neural Network to dynamically
modulate temperature (noise level) reactively based on polarization volatility and Gini context.

This is the third of three new liquid-NN training pipelines proposed by the
multi-agent analysis:

    Pipeline A: cfc_lambda_corrector  → modulates λ
    Pipeline B: cfc_landscape_modulator → modulates σ, attractor/repeller strengths
    Pipeline C: cfc_temp_modulator    (THIS FILE) → modulates T (temperature)

## Objective
Temperature acts as the stochastic "noise" in the Langevin dynamics.
High temperature allows agents to escape local minima (echo chambers).
Low temperature allows the system to settle into stable equilibria.

Physical Intuition for modulate T:
    - High polarization velocity + high skewness → temperature boost (escape echo chambers)
    - Low volatility → temperature decrease (less noise needed)
    - High Gini + high polarization → temperature boost (break inequality-amplified echo chambers)

## Architecture
    CfCCell(input_dim=5, hidden_size=32) → Linear(1) → Softplus
    Output is scaled via affine transform to [0.5, 2.0]:
    temp_multiplier = 0.5 + 1.5 * softplus(out) / (1 + softplus(out))

Input features (5):
    [polarization_t,          # current polarization index
     delta_polarization_t1,    # polarization velocity (1-step)
     delta_polarization_t5,    # polarization velocity (5-step window)
     skewness_t,               # opinion distribution skewness
     gini_coefficient]         # socioeconomic inequality

Target: temperature_multiplier in [0.5, 2.0]
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


def generate_temperature_training_data(n_trajectories: int = 10_000, seed: int = 42) -> dict:
    """Generate synthetic trajectories using the SocialEnergyEngine to learn
    the optimal temperature modulator.

    Args:
        n_trajectories: Number of synthetic trajectories to generate.
        seed: RNG seed.

    Returns:
        Dict with 'X' (features) and 'y' (target temperature multipliers).
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
        # Base params for this trajectory
        gini = float(rng.uniform(0.15, 0.65))
        lambda_social = float(rng.uniform(0.1, 0.5))
        base_temp = float(rng.uniform(0.01, 0.10))

        eng = SocialEnergyEngine(
            range_type="bipolar",
            temperature=base_temp,
            lambda_social=lambda_social,
            gini_coefficient=gini,
            seed=42 + i,
        )

        adj = random_network(N_agents, connectivity=connectivity, seed=42 + i)
        opinions = rng.uniform(-0.5, 0.5, N_agents)
        attractors = [{"position": 0.8, "strength": 1.0}, {"position": -0.8, "strength": 1.0}]
        repellers = [{"position": 0.0, "strength": 0.5}]

        pol_history = []
        op_history = []
        for _ in range(steps):
            opinions = eng.step(opinions, adj, attractors, repellers, eta=0.01)
            pol = float(np.std(opinions) / 1.0)
            pol_history.append(pol)
            op_history.append(opinions.copy())

        pol_arr = np.array(pol_history)
        for t in range(6, len(pol_arr) - 1):
            # Features
            pol_t = pol_arr[t]
            delta_t1 = pol_arr[t] - pol_arr[t - 1]
            delta_t5 = pol_arr[t] - pol_arr[t - 5] if t >= 5 else 0.0

            # Skewness of opinions at time t
            current_ops = op_history[t]
            # Standard skewness: E[(X-mu)^3] / sigma^3
            mu = np.mean(current_ops)
            sigma = np.std(current_ops)
            skewness = float(np.mean((current_ops - mu) ** 3) / (sigma**3 + 1e-6))

            # Target Logic (Physical Intuition)
            # default multiplier = 1.0
            multiplier = 1.0

            # 1. High polarization velocity + high skewness -> boost to escape echo chambers
            if delta_t1 > 0.01 and abs(skewness) > 0.5:
                multiplier += 0.4

            # 2. Low volatility -> decrease (less noise needed)
            volatility = float(
                np.std([pol_arr[t - j] - pol_arr[t - j - 1] for j in range(1, 4)])
                if t >= 3
                else 0.0
            )
            if volatility < 0.001:
                multiplier -= 0.3

            # 3. High Gini + high polarization -> boost to break inequality-amplified echo chambers
            if gini > 0.5 and pol_t > 0.4:
                multiplier += 0.3

            # Clamp target to [0.5, 2.0]
            target_temp_mult = float(np.clip(multiplier, 0.5, 2.0))

            features = [pol_t, delta_t1, delta_t5, skewness, gini]
            X_list.append(features)
            y_list.append(target_temp_mult)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)

    return {"X": X, "y": y}


def train_temperature_modulator(
    dataset: dict,
    hidden_size: int = 32,
    epochs: int = 50,
    lr: float = 3e-4,
    dt: float = 0.1,
) -> str:
    """Train the CfC temperature modulator.

    Args:
        dataset: Dict with 'X' (features) and 'y' (target multipliers).
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
    y = torch.tensor(dataset["y"], dtype=torch.float32).unsqueeze(1)

    input_dim = X.shape[1]
    cell = CfCCell(input_dim, hidden_size)
    readout = nn.Linear(hidden_size, 1)
    softplus = nn.Softplus()

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

    log.info(f"[CfC Temp] Starting training: {n_train} train, {n_val} val samples")

    BATCH_SIZE = 1024

    for epoch in range(epochs):
        # Training
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

            # Raw output through softplus
            raw_out = softplus(readout(h))
            # Affine transform: temp = 0.5 + 1.5 * softplus / (1 + softplus)
            # This maps [0, inf) to [0.5, 2.0)
            pred = 0.5 + 1.5 * raw_out / (1.0 + raw_out)

            loss = criterion(pred, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(cell.parameters()) + list(readout.parameters()), 1.0
            )
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / n_batches

        # Validation
        cell.eval()
        readout.eval()
        with torch.no_grad():
            h_val = torch.zeros(len(X_val), hidden_size)
            h_val = cell(h_val, X_val, dt=dt)
            raw_val = softplus(readout(h_val))
            val_pred = 0.5 + 1.5 * raw_val / (1.0 + raw_val)
            val_loss = criterion(val_pred, y_val)
            val_loss_val = val_loss.item()

        scheduler.step(val_loss_val)
        training_log["epochs"].append(epoch)
        training_log["train_loss"].append(train_loss)
        training_log["val_loss"].append(val_loss_val)

        if val_loss_val < best_val_loss:
            best_val_loss = val_loss_val
            patience_counter = 0
            model_path = CALIBRATED_DIR / "cfc_temperature.pt"
            torch.save(
                {"cell_state": cell.state_dict(), "readout_state": readout.state_dict()},
                model_path,
            )
        else:
            patience_counter += 1

        if epoch % 10 == 0 or epoch == epochs - 1:
            log.info(
                f"  Epoch {epoch}/{epochs}: train_loss={train_loss:.6f}, val_loss={val_loss_val:.6f}"
            )

        if patience_counter >= patience:
            log.info(f"  Early stopping at epoch {epoch}")
            break

    config = {
        "model_name": "CfCTempModulator-N5H32",
        "input_features": [
            "polarization_t",
            "delta_polarization_t1",
            "delta_polarization_t5",
            "skewness_t",
            "gini_coefficient",
        ],
        "target": "temperature_multiplier",
        "hidden_size": hidden_size,
        "epochs_run": len(training_log["epochs"]),
        "best_val_loss": best_val_loss,
        "architecture": "CfCCell(ODE) + Linear readout + Softplus + AffineScale([0.5, 2.0])",
    }
    (CALIBRATED_DIR / "cfc_temp_config.json").write_text(json.dumps(config, indent=2))
    (CALIBRATED_DIR / "cfc_temp_training_log.json").write_text(json.dumps(training_log, indent=2))

    log.info(f"[CfC Temp] Training complete. Best val loss: {best_val_loss:.6f}")
    return str(model_path)


def main():
    """Generate data, train, and save the temperature modulator model."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    log.info("=== Step 1: Generating training data ===")
    t0 = time.time()
    dataset = generate_temperature_training_data(n_trajectories=1000, seed=42)
    log.info(f"Data generation complete in {time.time() - t0:.1f}s")
    log.info(f"  Samples: {len(dataset['X'])}, Features: {dataset['X'].shape[1]}")

    log.info("=== Step 2: Training CfC Temperature Modulator ===")
    t0 = time.time()
    model_path = train_temperature_modulator(dataset, hidden_size=32, epochs=20, lr=3e-4)
    log.info(f"Training complete in {time.time() - t0:.1f}s")

    log.info("=== Step 3: Integration verification ===")
    import torch

    try:
        state = torch.load(model_path)
        log.info(f"Successfully loaded model from {model_path}")
        log.info(f"Keys in state: {list(state.keys())}")
    except Exception as e:
        log.error(f"Failed to load model: {e}")
        raise e

    return model_path


if __name__ == "__main__":
    main()
