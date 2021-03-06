# -*- coding: utf-8 -*-
"""Cartpole example."""

import numpy as np
import theano.tensor as T
from ..dynamics import AutoDiffDynamics, tensor_constrain


class CartpoleDynamics(AutoDiffDynamics):

    """Cartpole auto-differentiated dynamics model."""

    def __init__(self,
                 dt,
                 constrain=True,
                 min_bounds=-1.0,
                 max_bounds=1.0,
                 mc=1.0,
                 mp=0.1,
                 l=1.0,
                 g=9.80665,
                 **kwargs):
        """Cartpole dynamics.

        Args:
            dt: Time step [s].
            constrain: Whether to constrain the action space or not.
            min_bounds: Minimum bounds for action [N].
            max_bounds: Maximum bounds for action [N].
            mc: Cart mass [kg].
            mp: Pendulum mass [kg].
            l: Pendulum length [m].
            g: Gravity acceleration [m/s^2].
            **kwargs: Additional key-word arguments to pass to the
                AutoDiffDynamics constructor.

        Note:
            state: [x, x', sin(theta), cos(theta), theta']
            action: [F]
            theta: 0 is pointing up and increasing clockwise. 
        """
        self.constrained = constrain
        self.min_bounds = min_bounds
        self.max_bounds = max_bounds

        # Define inputs.
        x = T.dscalar("x")
        x_dot = T.dscalar("x_dot")
        sin_theta = T.dscalar("sin_theta")
        cos_theta = T.dscalar("cos_theta")
        theta_dot = T.dscalar("theta_dot")
        u = T.dscalar("u")

        x_inputs = [x, x_dot, sin_theta, cos_theta, theta_dot]
        u_inputs = [u]

        # Constrain action space.
        if constrain:
            F = tensor_constrain(u, min_bounds, max_bounds)
        else:
            F = u

        # Define dynamics model as per Razvan V. Florian's
        # "Correct equations for the dynamics of the cart-pole system".
        # Friction is neglected.

        # Eq. (23)
        temp = (F + mp * l * theta_dot**2 * sin_theta) / (mc + mp)
        numerator = g * sin_theta - cos_theta * temp
        denominator = l * (4.0 / 3.0 - mp * cos_theta**2 / (mc + mp))
        theta_dot_dot = numerator / denominator

        # Eq. (24)
        x_dot_dot = temp - mp * l * theta_dot_dot * cos_theta / (mc + mp)

        # Deaugment state for dynamics.
        theta = T.arctan2(sin_theta, cos_theta)
        next_theta = theta + theta_dot * dt

        f = T.stack([
            x + x_dot * dt,
            x_dot + x_dot_dot * dt,
            T.sin(next_theta),
            T.cos(next_theta),
            theta_dot + theta_dot_dot * dt,
        ])

        super(CartpoleDynamics, self).__init__(f, x_inputs, u_inputs, **kwargs)

    @classmethod
    def augment_state(cls, state):
        """Augments angular state into a non-angular state by replacing theta
        with sin(theta) and cos(theta).

        In this case, it converts:

            [x, x', theta, theta'] -> [x, x', sin(theta), cos(theta), theta']

        Args:
            state: State vector [reducted_state_size].

        Returns:
            Augmented state size [state_size].
        """
        if state.ndim == 1:
            x, x_dot, theta, theta_dot = state
        else:
            x = state[:, 0].reshape(-1, 1)
            x_dot = state[:, 1].reshape(-1, 1)
            theta = state[:, 2].reshape(-1, 1)
            theta_dot = state[:, 3].reshape(-1, 1)

        return np.hstack([x, x_dot, np.sin(theta), np.cos(theta), theta_dot])

    @classmethod
    def reduce_state(cls, state):
        """Reduces a non-angular state into an angular state by replacing
        sin(theta) and cos(theta) with theta.

        In this case, it converts:

            [x, x', sin(theta), cos(theta), theta'] -> [x, x', theta, theta']

        Args:
            state: Augmented state vector [state_size].

        Returns:
            Reduced state size [reducted_state_size].
        """
        if state.ndim == 1:
            x, x_dot, sin_theta, cos_theta, theta_dot = state
        else:
            x = state[:, 0].reshape(-1, 1)
            x_dot = state[:, 1].reshape(-1, 1)
            sin_theta = state[:, 2].reshape(-1, 1)
            cos_theta = state[:, 3].reshape(-1, 1)
            theta_dot = state[:, 4].reshape(-1, 1)

        theta = np.arctan2(sin_theta, cos_theta)
        return np.hstack([x, x_dot, theta, theta_dot])
