"""
Estimador común de matrices de transferencia electoral (inferencia ecológica).

Es el mismo estimador del Atlas CABA (`_inferencia.py` de ese repo), portado: una sola regresión
de mínimos cuadrados no negativos sobre toda la matriz, con la restricción «cada fila suma 1»
dentro de la estimación (no impuesta después, que deforma las celdas). En CABA eso bajó el error
de reconstrucción 2023→2025 de 5,3 % a 0,7 %.

Límite que no desaparece: describe circuitos, no personas. Para las celdas que el dato agregado
no identifica, las cotas de Duncan-Davis son la única afirmación sin supuestos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import nnls


def estimar(xm: np.ndarray, ym: np.ndarray, w: np.ndarray, lam: float = 1e4) -> np.ndarray:
    """Matriz B (k orígenes × m destinos), B ≥ 0 y filas que suman 1.

    xm: (n, k) proporciones de origen por unidad; ym: (n, m) proporciones de destino;
    w: (n,) ponderador (padrón)."""
    n, k = xm.shape
    m = ym.shape[1]
    A = np.zeros((n * m + k, k * m))
    c = np.zeros(n * m + k)
    sw = np.sqrt(w)
    for j in range(m):
        A[j * n:(j + 1) * n, j::m] = xm * sw[:, None]
        c[j * n:(j + 1) * n] = ym[:, j] * sw
    for i in range(k):
        A[n * m + i, i * m:(i + 1) * m] = lam
        c[n * m + i] = lam
    v, _ = nnls(A, c)
    B = v.reshape(k, m)
    s = B.sum(axis=1, keepdims=True)
    return B / np.where(s > 0, s, 1)


def cotas(x: pd.DataFrame, y: pd.DataFrame, peso: pd.Series, oi: str, dj: str) -> tuple[float, float]:
    """Cotas deterministas de Duncan-Davis (en %) para la celda origen oi -> destino dj."""
    xi, yj = x[oi].to_numpy(), y[dj].to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        lo = np.maximum(0.0, (yj - (1 - xi)) / np.where(xi > 0, xi, np.nan))
        hi = np.minimum(1.0, yj / np.where(xi > 0, xi, np.nan))
    w = peso.to_numpy() * xi
    ok = ~np.isnan(lo) & ~np.isnan(hi) & (w > 0)
    if not ok.any():
        return float("nan"), float("nan")
    return float(np.average(lo[ok], weights=w[ok]) * 100), float(np.average(hi[ok], weights=w[ok]) * 100)


def error_reconstruccion(x: pd.DataFrame, B: np.ndarray, y: pd.DataFrame, peso: pd.Series) -> float:
    """% de los votos (del destino) que el modelo no coloca donde están."""
    recon = (x.mul(peso, axis=0).to_numpy() @ B).sum(axis=0)
    real = y.mul(peso, axis=0).sum().to_numpy()
    return float(np.abs(recon - real).sum() / real.sum() * 100)
