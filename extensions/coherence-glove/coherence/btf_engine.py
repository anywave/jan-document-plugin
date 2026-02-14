"""
Bayesian Temporal Factorization for Multi-Wave Coherence Inference.

Production implementation based on Chen & Sun (2019) adapted for
real-time coherence modeling with φ-scaled priors.

Optimizations for production:
- Sliding window processing
- Warm start from previous posterior
- Reduced iterations for real-time
- NumPy vectorization

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy.stats import invwishart, gamma
from scipy import linalg

# Import φ-constants
try:
    from ra_constants import PHI, PHI_INVERSE, phi_power
except ImportError:
    PHI = 1.618033988749895
    PHI_INVERSE = 0.6180339887498949

    def phi_power(n: int) -> float:
        if n == 0:
            return 1.0
        elif n > 0:
            return PHI ** n
        else:
            return (1.0 / PHI) ** (-n)


# Band order for array indexing
BAND_ORDER = ['ULTRA', 'SLOW', 'CORE', 'FAST', 'RAPID']


@dataclass
class BTFResult:
    """Result of BTF inference.

    Attributes:
        W: Spatial factor matrix (N × R) - signal loadings
        X: Temporal factor matrix (T × R) - time evolution
        A: VAR coefficient matrices (L × R × R)
        Sigma_eps: Innovation covariance (R × R)
        tau: Observation precision
        uncertainty: Posterior uncertainty estimates
        converged: Whether inference converged
        n_iterations: Number of iterations run
    """
    W: np.ndarray
    X: np.ndarray
    A: List[np.ndarray]
    Sigma_eps: np.ndarray
    tau: float
    uncertainty: Dict[str, float]
    converged: bool
    n_iterations: int

    @property
    def band_amplitudes(self) -> np.ndarray:
        """Extract current band amplitudes (last time point)."""
        return np.abs(self.X[-1, :])

    @property
    def band_phases(self) -> np.ndarray:
        """Extract current band phases (last time point)."""
        # Use Hilbert transform for instantaneous phase
        from scipy.signal import hilbert
        analytic = hilbert(self.X, axis=0)
        return np.angle(analytic[-1, :])

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'W': self.W.tolist(),
            'X': self.X.tolist(),
            'A': [a.tolist() for a in self.A],
            'Sigma_eps': self.Sigma_eps.tolist(),
            'tau': self.tau,
            'uncertainty': self.uncertainty,
            'converged': self.converged,
            'n_iterations': self.n_iterations,
            'band_amplitudes': self.band_amplitudes.tolist(),
            'band_phases': self.band_phases.tolist(),
        }


class BTFEngine:
    """Bayesian Temporal Factorization engine for coherence inference.

    Decomposes multi-stream biometric signals into latent factors
    corresponding to φ-bands, with temporal dynamics modeled by VAR.
    """

    def __init__(self,
                 n_factors: int = 5,
                 var_lag: int = 3,
                 n_iterations: int = 100,
                 burn_in: int = 20,
                 convergence_threshold: float = 1e-4):
        """Initialize BTF engine.

        Args:
            n_factors: Latent dimension (5 for φ bands)
            var_lag: VAR lag order
            n_iterations: Max MCMC iterations (reduced for real-time)
            burn_in: Burn-in iterations
            convergence_threshold: Early stopping threshold
        """
        self.R = n_factors
        self.L = var_lag
        self.n_iter = n_iterations
        self.burn_in = burn_in
        self.convergence_threshold = convergence_threshold

        # φ-scaled prior precisions
        self.Lambda_W = self._build_spatial_prior()
        self.Lambda_A = self._build_var_prior()

        # Vague hyperparameters
        self.a_tau = 0.01
        self.b_tau = 0.01
        self.nu_0 = n_factors
        self.S_0 = np.eye(n_factors)

        # State for warm start
        self._prev_result: Optional[BTFResult] = None

    def _build_spatial_prior(self) -> np.ndarray:
        """Build φ-scaled spatial factor prior precision.

        Creates R×R precision matrix with φ-scaling that encourages
        smooth factor loadings. Central factors have lower precision
        (more flexibility), outer factors have higher precision.
        """
        Lambda = np.zeros((self.R, self.R))
        center = (self.R - 1) / 2.0
        for j in range(self.R):
            dist_from_center = abs(j - center)
            # Higher precision for factors further from center
            Lambda[j, j] = phi_power(dist_from_center)
        return Lambda

    def _build_var_prior(self) -> np.ndarray:
        """Build φ-scaled VAR coefficient prior precision.

        Encourages diagonal dominance with nearest-neighbor coupling.
        """
        Lambda = np.zeros((self.R, self.R))
        for j in range(self.R):
            for k in range(self.R):
                Lambda[j, k] = phi_power(2 - abs(j - k))
        return Lambda

    def fit(self,
            Y: np.ndarray,
            mask: Optional[np.ndarray] = None,
            warm_start: bool = True) -> BTFResult:
        """Fit BTF model via Gibbs sampling.

        Args:
            Y: Observation matrix (N × T), N signals, T time points
            mask: Binary mask, 1 = observed (default: all observed)
            warm_start: Initialize from previous fit if available

        Returns:
            BTFResult with posterior estimates
        """
        N, T = Y.shape
        if mask is None:
            mask = np.ones_like(Y)

        # Initialize (warm start or random)
        if warm_start and self._prev_result is not None:
            W, X, A, Sigma_eps, tau = self._warm_start_init(Y, mask)
        else:
            W, X, A, Sigma_eps, tau = self._random_init(N, T)

        # Track convergence
        prev_W = W.copy()
        converged = False

        # Gibbs sampling
        actual_iterations = 0
        for iteration in range(self.n_iter):
            actual_iterations = iteration + 1

            # Sample spatial factors
            W = self._sample_W(Y, X, tau, mask)

            # Sample temporal factors (with VAR)
            X = self._sample_X(Y, W, A, Sigma_eps, tau, mask)

            # Sample VAR coefficients
            A = self._sample_A(X, Sigma_eps)

            # Sample innovation covariance
            Sigma_eps = self._sample_Sigma_eps(X, A)

            # Sample observation precision
            tau = self._sample_tau(Y, W, X, mask)

            # Check convergence (after burn-in)
            if iteration >= self.burn_in:
                W_change = np.max(np.abs(W - prev_W))
                if W_change < self.convergence_threshold:
                    converged = True
                    break
                prev_W = W.copy()

        # Compute uncertainty estimates
        uncertainty = self._compute_uncertainty(Y, W, X, tau, mask)

        result = BTFResult(
            W=W,
            X=X,
            A=A,
            Sigma_eps=Sigma_eps,
            tau=tau,
            uncertainty=uncertainty,
            converged=converged,
            n_iterations=actual_iterations,
        )

        # Store for warm start
        self._prev_result = result

        return result

    def _random_init(self, N: int, T: int) -> Tuple:
        """Random initialization."""
        W = np.random.randn(N, self.R) / np.sqrt(PHI)
        X = np.random.randn(T, self.R) / np.sqrt(PHI)
        A = [np.eye(self.R) * 0.1 for _ in range(self.L)]
        Sigma_eps = np.eye(self.R)
        tau = 1.0
        return W, X, A, Sigma_eps, tau

    def _warm_start_init(self, Y: np.ndarray, mask: np.ndarray) -> Tuple:
        """Initialize from previous result (sliding window)."""
        prev = self._prev_result
        N, T = Y.shape
        prev_T = prev.X.shape[0]

        # Reuse spatial factors
        W = prev.W.copy()

        # Extend/truncate temporal factors
        if T == prev_T:
            X = prev.X.copy()
        elif T > prev_T:
            # Extend with VAR forecast
            X = np.zeros((T, self.R))
            X[:prev_T, :] = prev.X
            for t in range(prev_T, T):
                X[t, :] = sum(prev.A[l] @ X[t-l-1, :] for l in range(self.L))
        else:
            # Truncate to recent
            X = prev.X[-T:, :].copy()

        A = [a.copy() for a in prev.A]
        Sigma_eps = prev.Sigma_eps.copy()
        tau = prev.tau

        return W, X, A, Sigma_eps, tau

    def _sample_W(self, Y: np.ndarray, X: np.ndarray,
                  tau: float, mask: np.ndarray) -> np.ndarray:
        """Sample spatial factors row-wise."""
        N, T = Y.shape
        W = np.zeros((N, self.R))

        Lambda_W_inv = np.linalg.inv(self.Lambda_W)

        for n in range(N):
            obs_t = np.where(mask[n, :] == 1)[0]
            if len(obs_t) == 0:
                W[n, :] = np.random.multivariate_normal(
                    np.zeros(self.R), Lambda_W_inv
                )
                continue

            X_obs = X[obs_t, :]
            y_obs = Y[n, obs_t]

            # Posterior precision and mean
            precision = self.Lambda_W + tau * X_obs.T @ X_obs
            Sigma_n = np.linalg.inv(precision)
            mu_n = Sigma_n @ (tau * X_obs.T @ y_obs)

            W[n, :] = np.random.multivariate_normal(mu_n, Sigma_n)

        return W

    def _sample_X(self, Y: np.ndarray, W: np.ndarray,
                  A: List[np.ndarray], Sigma_eps: np.ndarray,
                  tau: float, mask: np.ndarray) -> np.ndarray:
        """Sample temporal factors with VAR constraint."""
        N, T = Y.shape
        X = np.zeros((T, self.R))

        try:
            Sigma_eps_inv = np.linalg.inv(Sigma_eps)
        except np.linalg.LinAlgError:
            Sigma_eps_inv = np.eye(self.R)

        # Sample initial states from prior
        for t in range(min(self.L, T)):
            X[t, :] = np.random.multivariate_normal(
                np.zeros(self.R), Sigma_eps
            )

        # Sample remaining states
        for t in range(self.L, T):
            obs_n = np.where(mask[:, t] == 1)[0]
            W_obs = W[obs_n, :]
            y_obs = Y[obs_n, t]

            # VAR mean
            var_mean = sum(A[l] @ X[t-l-1, :] for l in range(self.L))

            # Posterior precision
            if len(obs_n) > 0:
                precision = tau * W_obs.T @ W_obs + Sigma_eps_inv
            else:
                precision = Sigma_eps_inv.copy()

            # Add future terms (for non-final t)
            for l in range(1, min(self.L + 1, T - t)):
                if t + l < T:
                    precision += A[l-1].T @ Sigma_eps_inv @ A[l-1]

            try:
                Sigma_t = np.linalg.inv(precision)
            except np.linalg.LinAlgError:
                Sigma_t = np.eye(self.R) * 0.1

            if len(obs_n) > 0:
                mu_t = Sigma_t @ (
                    tau * W_obs.T @ y_obs +
                    Sigma_eps_inv @ var_mean
                )
            else:
                mu_t = Sigma_t @ (Sigma_eps_inv @ var_mean)

            X[t, :] = np.random.multivariate_normal(mu_t, Sigma_t)

        return X

    def _sample_A(self, X: np.ndarray,
                  Sigma_eps: np.ndarray) -> List[np.ndarray]:
        """Sample VAR coefficients."""
        T = X.shape[0]

        try:
            Sigma_eps_inv = np.linalg.inv(Sigma_eps)
        except np.linalg.LinAlgError:
            Sigma_eps_inv = np.eye(self.R)

        A_new = []
        for l in range(self.L):
            # Build regression matrices
            if T <= self.L:
                A_new.append(np.eye(self.R) * 0.1)
                continue

            Y_var = X[self.L:, :]
            Z_l = X[self.L-l-1:T-l-1, :]

            # Posterior precision
            try:
                precision = self.Lambda_A + Z_l.T @ Z_l
                Sigma_A = np.linalg.inv(precision)
            except np.linalg.LinAlgError:
                Sigma_A = np.eye(self.R) * 0.1

            # Compute residual
            if l > 0:
                residual = Y_var.copy()
                for ll in range(l):
                    residual -= (A_new[ll] @ X[self.L-ll-1:T-ll-1, :].T).T
            else:
                residual = Y_var

            mu_A = Sigma_A @ (Z_l.T @ residual)

            # Sample
            A_l = np.zeros((self.R, self.R))
            for r in range(self.R):
                A_l[r, :] = np.random.multivariate_normal(
                    mu_A[:, r], Sigma_A
                )

            A_new.append(A_l)

        return A_new

    def _sample_Sigma_eps(self, X: np.ndarray,
                          A: List[np.ndarray]) -> np.ndarray:
        """Sample innovation covariance."""
        T = X.shape[0]

        if T <= self.L:
            return np.eye(self.R)

        # Compute residuals
        residuals = np.zeros((T - self.L, self.R))
        for t in range(self.L, T):
            var_mean = sum(A[l] @ X[t-l-1, :] for l in range(self.L))
            residuals[t - self.L, :] = X[t, :] - var_mean

        # Wishart posterior
        S_post = self.S_0 + residuals.T @ residuals
        nu_post = self.nu_0 + T - self.L

        # Sample inverse Wishart
        try:
            Sigma_eps = invwishart.rvs(df=nu_post, scale=S_post)
        except:
            Sigma_eps = np.eye(self.R)

        return Sigma_eps

    def _sample_tau(self, Y: np.ndarray, W: np.ndarray,
                    X: np.ndarray, mask: np.ndarray) -> float:
        """Sample observation precision."""
        # Compute residuals
        Y_pred = W @ X.T
        residuals = (Y - Y_pred) * mask
        ss = np.sum(residuals ** 2)
        n_obs = np.sum(mask)

        if n_obs == 0:
            return 1.0

        # Gamma posterior
        a_post = self.a_tau + n_obs / 2
        b_post = self.b_tau + ss / 2

        return gamma.rvs(a=a_post, scale=1/b_post)

    def _compute_uncertainty(self, Y: np.ndarray, W: np.ndarray,
                              X: np.ndarray, tau: float,
                              mask: np.ndarray) -> Dict[str, float]:
        """Compute posterior uncertainty estimates."""
        # Reconstruction error
        Y_pred = W @ X.T
        residuals = (Y - Y_pred) * mask
        n_obs = np.sum(mask)

        if n_obs > 0:
            rmse = np.sqrt(np.sum(residuals ** 2) / n_obs)
        else:
            rmse = 1.0

        # Observation noise std
        obs_std = np.sqrt(1 / tau) if tau > 0 else 1.0

        # Band-specific uncertainty (from X variance)
        band_uncertainty = np.std(X, axis=0)

        return {
            'rmse': float(rmse),
            'observation_std': float(obs_std),
            'band_uncertainties': band_uncertainty.tolist(),
            'mean_band_uncertainty': float(np.mean(band_uncertainty)),
        }

    def predict(self, horizon: int) -> Tuple[np.ndarray, np.ndarray]:
        """Forecast future latent states.

        Args:
            horizon: Number of steps ahead

        Returns:
            (X_pred, uncertainty) - predicted factors and uncertainty
        """
        if self._prev_result is None:
            raise ValueError("Must call fit() before predict()")

        result = self._prev_result
        T = result.X.shape[0]

        # VAR forecast
        X_extended = np.vstack([result.X, np.zeros((horizon, self.R))])

        for h in range(horizon):
            t = T + h
            X_extended[t, :] = sum(
                result.A[l] @ X_extended[t-l-1, :]
                for l in range(self.L)
            )

        X_pred = X_extended[T:, :]

        # Uncertainty grows with horizon
        base_std = np.sqrt(np.diag(result.Sigma_eps))
        uncertainty = np.outer(np.arange(1, horizon + 1), base_std)

        return X_pred, uncertainty

    def reset(self) -> None:
        """Reset warm start state."""
        self._prev_result = None


def create_btf_engine(real_time: bool = True) -> BTFEngine:
    """Factory function to create BTF engine with appropriate settings.

    Args:
        real_time: If True, use reduced iterations for faster inference.
                   Note: Pure Python is ~1-2s per fit. Production should use
                   GPU acceleration (see Task 13: Performance Optimization).

    Returns:
        Configured BTFEngine
    """
    if real_time:
        return BTFEngine(
            n_factors=5,
            var_lag=3,
            n_iterations=25,  # Minimal for fast feedback
            burn_in=5,
            convergence_threshold=5e-3,
        )
    else:
        return BTFEngine(
            n_factors=5,
            var_lag=3,
            n_iterations=200,
            burn_in=50,
            convergence_threshold=1e-4,
        )
