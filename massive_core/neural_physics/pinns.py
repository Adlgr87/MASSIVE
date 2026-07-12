"""Physics-informed neural-network baseline for MASSIVE residuals."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class PhysicsInformedNeuralNetwork(nn.Module):
    """Small PINN with data and physics residual losses.

    Args:
        input_dim: Input dimension, usually state plus time.
        hidden_dim: Hidden-layer width.
        output_dim: Output dimension.
    """

    def __init__(self, input_dim: int = 2, hidden_dim: int = 64, output_dim: int = 1) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        """Evaluate the neural network.

        Args:
            inputs: Tensor of shape ``(batch, input_dim)``.

        Returns:
            Predicted output tensor.
        """

        return self.net(inputs)

    def physics_loss(self, x: torch.Tensor, t: torch.Tensor, social_force: torch.Tensor | None = None) -> torch.Tensor:
        """Compute a Langevin-like residual loss.

        Args:
            x: State tensor with gradients enabled or enableable.
            t: Time tensor.
            social_force: Optional known force tensor. If omitted, zero force
                is used.

        Returns:
            Mean squared residual.
        """

        x = x.requires_grad_(True)
        t = t.requires_grad_(True)
        u = self.forward(torch.cat([x, t], dim=-1))
        u_t = torch.autograd.grad(u, t, grad_outputs=torch.ones_like(u), create_graph=True)[0]
        grad_u = torch.autograd.grad(u, x, grad_outputs=torch.ones_like(u), create_graph=True)[0]
        force = torch.zeros_like(grad_u) if social_force is None else social_force
        residual = u_t + grad_u - force
        return torch.mean(residual**2)

    def training_loss(
        self,
        inputs: torch.Tensor,
        targets: torch.Tensor,
        x: torch.Tensor,
        t: torch.Tensor,
        physics_weight: float = 0.5,
    ) -> torch.Tensor:
        """Combine data loss and physics residual loss.

        Args:
            inputs: Supervised input tensor.
            targets: Supervised target tensor.
            x: State tensor for physics residual.
            t: Time tensor for physics residual.
            physics_weight: Weight in ``[0, 1]`` for physics loss.

        Returns:
            Weighted scalar loss.
        """

        if not 0.0 <= physics_weight <= 1.0:
            raise ValueError("physics_weight must be in [0, 1]")
        data_loss = F.mse_loss(self.forward(inputs), targets)
        residual_loss = self.physics_loss(x, t)
        return (1.0 - physics_weight) * data_loss + physics_weight * residual_loss
