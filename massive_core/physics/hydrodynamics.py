"""Continuum hydrodynamic approximations for large agent populations."""

from __future__ import annotations

import numpy as np

Array = np.ndarray


class AgentHydrodynamics:
    """Treats one-dimensional agent opinions as a density field.

    Args:
        grid: Optional grid over opinion space.
        diffusivity: Non-negative diffusion coefficient.
    """

    def __init__(self, grid: Array | None = None, diffusivity: float = 0.01) -> None:
        if diffusivity < 0.0:
            raise ValueError("diffusivity must be non-negative")
        self.grid = np.asarray(grid, dtype=float) if grid is not None else np.linspace(-1.0, 1.0, 100)
        self.diffusivity = diffusivity

    def compute_density_field(self, agent_positions: Array, kernel_bandwidth: float = 0.1) -> Array:
        """Estimate density with a Gaussian kernel.

        Args:
            agent_positions: Agent positions or opinions.
            kernel_bandwidth: Positive kernel bandwidth.

        Returns:
            Density normalized to integrate to one on the grid.
        """

        if kernel_bandwidth <= 0.0:
            raise ValueError("kernel_bandwidth must be positive")
        positions = np.asarray(agent_positions, dtype=float).reshape(-1)
        if positions.size == 0:
            return np.zeros_like(self.grid)
        diff = (self.grid[:, None] - positions[None, :]) / kernel_bandwidth
        density = np.mean(np.exp(-0.5 * diff**2), axis=1) / (kernel_bandwidth * np.sqrt(2.0 * np.pi))
        integral = np.trapezoid(density, self.grid)
        if integral > 0.0:
            density = density / integral
        return density

    def compute_velocity_field(self, density: Array, force_field: Array | None = None) -> Array:
        """Compute a Darcy-like velocity field.

        Args:
            density: Density samples on ``self.grid``.
            force_field: Optional external force sampled on the grid.

        Returns:
            Velocity field.
        """

        rho = np.asarray(density, dtype=float)
        grad_pressure = np.gradient(rho, self.grid)
        permeability = 1.0 / (1.0 + rho**2)
        velocity = -permeability * grad_pressure
        if force_field is not None:
            velocity = velocity + np.asarray(force_field, dtype=float)
        return velocity

    def solve_fluid_equations(self, initial_density: Array, dt: float, n_steps: int, force_field: Array | None = None) -> Array:
        """Solve a one-dimensional advection-diffusion equation.

        Args:
            initial_density: Initial density on ``self.grid``.
            dt: Positive time step.
            n_steps: Number of updates.
            force_field: Optional external force field.

        Returns:
            Final non-negative normalized density.
        """

        if dt <= 0.0:
            raise ValueError("dt must be positive")
        rho = np.asarray(initial_density, dtype=float).copy()
        for _ in range(n_steps):
            velocity = self.compute_velocity_field(rho, force_field)
            advection = -np.gradient(rho * velocity, self.grid)
            diffusion = self.diffusivity * np.gradient(np.gradient(rho, self.grid), self.grid)
            rho = np.clip(rho + dt * (advection + diffusion), 0.0, None)
            integral = np.trapezoid(rho, self.grid)
            if integral > 0.0:
                rho = rho / integral
        return rho
