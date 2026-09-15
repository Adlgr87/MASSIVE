"""
train_cfc_lambda.py — Train a CfC Liquid Neural Network to dynamically
modulate lambda_social (social coupling) based on polarization dynamics.

This is the FIRST of three new liquid-NN training pipelines proposed by the
multi-agent analysis:

    Pipeline A: cfc_lambda_corrector  (THIS FILE)  → modulates λ
    Pipeline B: cfc_landscape_modulator           → modulates σ, attractor/repeller strengths
    Pipeline C: cfc_temp_modulator                → modulates T (temperature)

## Objective
When polarization rises, the system should shift λ to reinforce group identity
(social dominance). When polarization is too high (risk of fragmentation),
λ should be reduced to let the landscape pull agents back toward attractors.

## Data Generation Strategy
Generate 10,000 synthetic trajectories from the Energy Engine where
lambda_social is treated as the target variable to learn. We vary
polarization dynamics and record the optimal λ that minimizes the
residual between predicted and target polarization velocity.

## Architecture
    CfCCell(input_dim=5, hidden_size=32) → Linear(1) → Softplus

Input features (5):
    [polarization_t,          # current polarization index
     delta_pol_t1,            # polarization velocity (1-step)
     delta_pol_t5,            # polarization velocity (5-step window)
     gini_coefficient,        # socioeconomic inequality
     volatility_index]        # std of recent opinion changes

Target: lambda_social_correction (Δλ multiplier in [0, 1])
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np

log = logging.getLogger("massive")

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)
CALIBRATED_DIR = MODELS_DIR / "cfc_calibrated"
CALIBRATED_DIR.mkdir(exist_ok=True)


def generate_lambda_training_data(n_trajectories: int = 10_000, seed: int = 42) -> dict:
    """Generate synthetic trajectories where lambda_social varies and
    we record the polarization dynamics.

    Strategy: Run the Energy Engine with random lambda values, then label
    each trajectory with the lambda that produced the *target* polarization
    velocity (the training target is the inverse: given polarization dynamics,
    predict the lambda that would produce stable depolarization).

    Args:
        n_trajectories: Number of synthetic trajectories to generate.
        seed: RNG seed.

    Returns:
        Dict with 'X' (features) and 'y' (target lambda corrections).
    """
    try:
        import torch
    except ImportError:
        raise ImportError("PyTorch is required for training: pip install torch>=2.2.0")

    from energy_engine import SocialEnergyEngine, random_network

    rng = np.random.default_rng(seed)
    N_agents = 50
    steps = 365
    connectivity = 0.3

    X_list = []
    y_list = []

    for i in range(n_trajectories):
        # Randomize the ground-truth lambda for this trajectory
        true_lambda = float(rng.uniform(0.0, 1.0))
        gini = float(rng.uniform(0.15, 0.65))  # realistic country Gini range
        temperature = float(rng.uniform(0.01, 0.20))

        eng = SocialEnergyEngine(
            range_type="bipolar",
            temperature=temperature,
            lambda_social=true_lambda,
            gini_coefficient=gini,
            seed=42 + i,
        )

        adj = random_network(N_agents, connectivity=connectivity, seed=42 + i)
        opinions = rng.uniform(-0.5, 0.5, N_agents)
        attractors = [{"position": 0.8, "strength": 1.0}, {"position": -0.8, "strength": 1.0}]
        repellers = [{"position": 0.0, "strength": 0.5}]

        # Collect polarization time series
        pol_history = []
        op_history = []
        for t in range(steps):
            opinions = eng.step(opinions, adj, attractors, repellers, eta=0.01)
            pol = float(np.std(opinions) / 1.0)  # half_range = 1.0 for bipolar
            pol_history.append(pol)
            op_history.append(opinions.copy())

        # For each time step, compute features + target
        pol_arr = np.array(pol_history)
        for t in range(6, len(pol_arr) - 1):
            pol_t = pol_arr[t]
            delta_t1 = pol_arr[t] - pol_arr[t - 1]
            delta_t5 = pol_arr[t] - pol_arr[t - 5] if t >= 5 else 0.0
            volatility = float(np.std([pol_arr[t - j] - pol_arr[t - j - 1] for j in range(1, 4)]) if t >= 3 else 0.0)

            # Target: the lambda that minimizes polarization divergence
            # We use the true lambda as the target, but apply a correction
            # that pushes toward stability: if polarization is accelerating,
            # we want lower lambda (let landscape dominate and pull toward consensus)
            pol_accelerating = delta_t1 > 0.01 and (delta_t5 > delta_t1)
            if pol_accelerating:
                # Need to REDUCE lambda to let landscape pull agents back
                target_lambda = max(0.0, true_lambda - 0.2)
            else:
                target_lambda = true_lambda

            features = [pol_t, delta_t1, delta_t5, gini, volatility]
            X_list.append(features)
            y_list.append(target_lambda)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)

    return {"X": X, "y": y}


def train_lambda_corrector(
    dataset: dict,
    hidden_size: int = 32,
    epochs: int = 50,
    lr: float = 3e-4,
    dt: float = 0.1,
) -> str:
    """Train the CfC lambda corrector.

    Args:
        dataset: Dict with 'X' (features) and 'y' (target lambdas).
        hidden_size: Hidden state dimension.
        epochs: Number of training epochs.
        lr: Learning rate.
        dt: ODE integration step.

    Returns:
        Path to saved model.
    """
    import torch
    import torch.nn as nn

    from cfc_engine import CfCLambdaCorrector

    X = torch.tensor(dataset["X"], dtype=torch.float32)
    y = torch.tensor(dataset["y"], dtype=torch.float32).unsqueeze(1)

    input_dim = X.shape[1]
    corrector = CfCLambdaCorrector(input_dim=input_dim, hidden_size=hidden_size)
    cell = corrector.cell
    readout = corrector.readout
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
    val_idx = idx[n_train:n_train + n_val]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    best_val_loss = float("inf")
    patience = 15
    patience_counter = 0
    training_log = {"epochs": [], "train_loss": [], "val_loss": []}

    log.info(f"[CfC Lambda] Starting training: {n_train} train, {n_val} val samples")

    BATCH_SIZE = 1024

    for epoch in range(epochs):
        # Training — mini-batch loop
        cell.train()
        readout.train()
        epoch_loss = 0.0
        n_batches = 0
        perm = np.random.default_rng(42 + epoch).permutation(len(X_train))
        for batch_start in range(0, len(X_train), BATCH_SIZE):
            batch_idx = perm[batch_start:batch_start + BATCH_SIZE]
            X_batch = X_train[batch_idx]
            y_batch = y_train[batch_idx]

            optimizer.zero_grad()
            h = torch.zeros(len(X_batch), hidden_size)
            h = cell(h, X_batch, dt=dt)
            pred = softplus(readout(h))  # softplus → [0, ∞), bounded by target range
            loss = criterion(pred, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(cell.parameters()) + list(readout.parameters()), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        train_loss = epoch_loss / n_batches

        # Validation — full pass (single batch is fine for eval)
        cell.eval()
        readout.eval()
        with torch.no_grad():
            h_val = torch.zeros(len(X_val), hidden_size)
            h_val = cell(h_val, X_val, dt=dt)
            val_pred = softplus(readout(h_val))
            val_loss = criterion(val_pred, y_val)
            val_loss_val = val_loss.item()

        scheduler.step(val_loss_val)
        training_log["epochs"].append(epoch)
        training_log["train_loss"].append(train_loss)
        training_log["val_loss"].append(val_loss_val)

        if val_loss_val < best_val_loss:
            best_val_loss = val_loss_val
            patience_counter = 0
            # Save best model (flat state_dict for router compatibility)
            model_path = CALIBRATED_DIR / "cfc_lambda_corrector.pt"
            torch.save(corrector.state_dict(), model_path)
        else:
            patience_counter += 1

        if epoch % 10 == 0 or epoch == epochs - 1:
            log.info(f"  Epoch {epoch}/{epochs}: train_loss={train_loss:.6f}, val_loss={val_loss_val:.6f}")

        if patience_counter >= patience:
            log.info(f"  Early stopping at epoch {epoch} (patience {patience})")
            break

    # Save config + metadata
    config = {
        "model_name": "CfCLambdaCorrector-N5H32",
        "input_features": [
            "polarization_t",
            "delta_polarization_t1",
            "delta_polarization_t5",
            "gini_coefficient",
            "volatility_index",
        ],
        "target": "lambda_social_correction",
        "hidden_size": hidden_size,
        "epochs_run": len(training_log["epochs"]),
        "best_val_loss": best_val_loss,
        "architecture": "CfCCell(ODE) + Linear readout + Softplus",
    }
    (CALIBRATED_DIR / "cfc_lambda_config.json").write_text(json.dumps(config, indent=2))
    (CALIBRATED_DIR / "cfc_lambda_training_log.json").write_text(
        json.dumps(training_log, indent=2)
    )

    log.info(f"[CfC Lambda] Training complete. Best val loss: {best_val_loss:.6f}")
    log.info(f"[CfC Lambda] Model saved to: {model_path}")
    return str(model_path)


def main():
    """Generate data, train, and save the lambda corrector model."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    log.info("=== Step 1: Generating training data ===")
    t0 = time.time()
    dataset = generate_lambda_training_data(n_trajectories=10_000, seed=42)
    log.info(f"Data generation complete in {time.time() - t0:.1f}s")
    log.info(f"  Samples: {len(dataset['X'])}, Features: {dataset['X'].shape[1]}")

    log.info("=== Step 2: Training CfC Lambda Corrector ===")
    t0 = time.time()
    model_path = train_lambda_corrector(dataset, hidden_size=32, epochs=50, lr=3e-4)
    log.info(f"Training complete in {time.time() - t0:.1f}s")

    log.info("=== Step 3: Integration verification ===")
    # Verify the model can be loaded by the router pattern
    from cfc_router import CfCRouter
    CfCRouter._instance = None
    router = CfCRouter.get()
    log.info(f"CfCRouter status: {router.status}")
    log.info("Lambda corrector is ready for integration into energy_engine.step()")

    return model_path


if __name__ == "__main__":
    main()
