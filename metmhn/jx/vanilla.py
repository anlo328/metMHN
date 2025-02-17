from metmhn.jx.kronvec import (k2d1t, 
                               k2ntt, 
                               k2dt0,
                               k2d10,
                               k2d0t
                               )
import numpy as np
import jax.numpy as jnp
from jax import jit, lax, vmap
from functools import partial



@jit
def t(z: jnp.ndarray) -> tuple[jnp.ndarray, float]:
    z = z.reshape((-1, 2), order="C")
    val = z.sum()
    return z.flatten(order="F"), val


@jit
def f(z: jnp.ndarray) -> tuple[jnp.ndarray, float]:
    z = z.reshape((-1, 2), order="C")
    val = z[:, 1].sum()
    return z.flatten(order="F"), val


@partial(jit, static_argnames=["diag", "transpose"])
def _kronvec(
    log_theta: jnp.ndarray,
    p: jnp.ndarray,
    i: int,
    state: jnp.ndarray,
    diag: bool = True,
    transpose: bool = False
    ) -> jnp.ndarray:

    def loop_body_diag(j, val):

        val = lax.switch(
            index=state[j],
            branches=[
                lambda x: x,
                lambda x: k2d1t(p=x, theta=jnp.exp(
                    log_theta[i, j]))
            ],
            operand=val
        )
        return val
    
    n = log_theta.shape[0]
    # Diagonal Kronecker factors
    p = lax.fori_loop(lower=0, upper=i,
                      body_fun=loop_body_diag, init_val=p)

    # Non-diagonal Kronecker factor
    p = lax.switch(
        index=state[i],
        branches=[
            lambda x: -jnp.exp(log_theta[i, i]) * x,
            lambda x: k2ntt(p=x, theta=jnp.exp(log_theta[i, i]),
                            diag=diag, transpose=transpose),
        ],
        operand=p
    )

    # Diagonal Kronecker factors
    p = lax.fori_loop(lower=i+1, upper=n,
                      body_fun=loop_body_diag, init_val=p)

    return p


@partial(jit, static_argnames=["diag", "transpose"])
def kronvec_i(
    log_theta: jnp.ndarray,
    p: jnp.ndarray,
    i: int,
    state: jnp.ndarray,
    diag: bool = True,
    transpose: bool = False
    ) -> jnp.ndarray:
    return lax.cond(
        not diag and state[i] != 1,
        lambda: jnp.zeros_like(p),
        lambda: _kronvec(
            log_theta=log_theta,
            p=p,
            i=i,
            state=state,
            diag=diag,
            transpose=transpose
        ),
    )


@partial(jit, static_argnames=["diag", "transpose"])
def kronvec(log_theta: jnp.ndarray, p: jnp.ndarray, state: jnp.ndarray, 
            diag: bool = True, transpose: bool = False) -> jnp.ndarray:
    """This computes the restricted version of the product of the rate matrix Q with a vector Q p.

    Args:
        log_theta (jnp.ndarray): Log values of the theta matrix
        p (jnp.ndarray): Vector to multiply with from the right. Length must equal the number of
            nonzero entries in the state vector.
        n (int): Total number of events in the MHN.
        state (jnp.ndarray): Binary state vector, representing the current sample's events.
        diag (bool, optional): Whether to use the diagonal of Q (and not set it to 0). Defaults to True.
        transpose (bool, optional): Whether to transpose Q before multiplying. Defaults to False.

    Returns:
        jnp.array: Q p or p^T Q
    """

    def body_fun(i, val):

        val += kronvec_i(log_theta=log_theta, p=p, i=i,
                         state=state, diag=diag, transpose=transpose)

        return val
    n = log_theta.shape[0]
    state_size = np.log2(p.shape[0]).astype(int)
    return lax.fori_loop(
        lower=0,
        upper=n,
        body_fun=body_fun,
        init_val=jnp.zeros(shape=2**state_size)
    )

@jit
def scal_d_pt(log_d_p: jnp.ndarray, log_d_m: jnp.ndarray, state: jnp.ndarray, 
              vec: jnp.ndarray) -> jnp.ndarray:
    def loop_body_diag(j, val):
        val = lax.cond(state[j] == 1,
                        lambda x: (k2d1t(p=x[0], theta=jnp.exp(log_d_p[j])),
                                  k2d1t(p=x[1], theta=jnp.exp(log_d_m[j]))),
                       lambda x: x,
                       operand=val
                       )
        return val
    n = log_d_m.shape[0]
    p = lax.fori_loop(lower=0, upper=n-1, 
                      body_fun=loop_body_diag, init_val=(vec, vec))
    return k2d10(p[0]) , k2d0t(p[1], jnp.exp(log_d_m[-1]))


def _d_scal_d_pt(log_d_p: jnp.ndarray, log_d_m: jnp.ndarray, state: jnp.ndarray, 
              vec: jnp.ndarray, i: int) -> jnp.ndarray:
    def loop_body_diag(j, val):
        val = lax.cond(state[j] == 1,
                        lambda x: (k2d1t(p=x[0], theta=jnp.exp(log_d_p[j])),
                                  k2d1t(p=x[1], theta=jnp.exp(log_d_m[j]))),
                       lambda x: x,
                       operand=val
                       )
        return val
    n = log_d_m.shape[0] - 1
    p = lax.fori_loop(lower=0, upper=i, 
                      body_fun=loop_body_diag, init_val=(vec, vec))
    d_p = k2d0t(p[0], jnp.exp(log_d_p[i]))
    d_m = k2d0t(p[1], jnp.exp(log_d_m[i]))
    
    p = lax.fori_loop(lower=i+1, upper=n, 
                      body_fun=loop_body_diag, init_val=(d_p, d_m))
    
    return k2d10(p[0]),  k2d0t(p[1], jnp.exp(log_d_m[-1]))

@jit 
def d_scal_d_pt(log_d_p: jnp.ndarray, log_d_m: jnp.ndarray, state: jnp.ndarray, 
              vec: jnp.ndarray, i:int) -> jnp.ndarray:
    n = log_d_p.shape[0]-1
    return lax.switch(state[i] + (i==n),
                    [lambda: (0*vec, 0*vec),
                    lambda: _d_scal_d_pt(log_d_p, log_d_m, state, vec, i),
                    lambda: (0*vec, scal_d_pt(log_d_p, log_d_m, state, vec)[1])]
    )

@jit
def x_partial_D_y(log_d_p: jnp.ndarray, log_d_m: jnp.ndarray, state: jnp.ndarray, 
              x: jnp.ndarray, y:jnp.array):
    def body_fun(i, carry):
        d_dp, d_dm = d_scal_d_pt(log_d_p, log_d_m, state, y, i)
        a = carry[0].at[i].set(jnp.dot(x, d_dp))
        b = carry[1].at[i].set(jnp.dot(x, d_dm))
        return (a,b)
    n = log_d_p.shape[0]
    d_p, d_m = lax.fori_loop(0, n, body_fun,(jnp.zeros_like(log_d_p), jnp.zeros_like(log_d_m)))
    return d_p, d_m


def kron_diag_i(
        log_theta: jnp.ndarray,
        i: int,
        state: jnp.ndarray,
        diag: jnp.ndarray) -> jnp.ndarray:

    n = log_theta.shape[0]

    def loop_body(j, val):
        val = lax.switch(
            index=state[j],
            branches=[
                lambda val: val,
                lambda val: k2d1t(val, jnp.exp(log_theta[i, j])),
            ],
            operand=val
        )
        return val

    diag = lax.fori_loop(
        lower=0,
        upper=i,
        body_fun=loop_body,
        init_val=diag
    )

    diag = lax.switch(
        index=state[i],
        branches=[
            lambda val: -jnp.exp(log_theta[i, i]) * val,
            lambda val: k2dt0(val, jnp.exp(log_theta[i, i])),
        ],
        operand=diag
    )

    diag = lax.fori_loop(
        lower=i+1,
        upper=n,
        body_fun=loop_body,
        init_val=diag
    )

    return diag


@jit
def kron_diag(
        log_theta: jnp.ndarray,
        state: jnp.ndarray,
        diag: jnp.ndarray
        ) -> jnp.ndarray:

    def body_fun(i, val):
        val += kron_diag_i(log_theta=log_theta, i=i, state=state, diag=diag)
        return val

    n = log_theta.shape[0]

    return lax.fori_loop(
        lower=0,
        upper=n,
        body_fun=body_fun,
        init_val=jnp.zeros_like(diag)
    )


@partial(jit, static_argnames=["transpose"])
def R_inv_vec(log_theta: jnp.ndarray, 
              x: jnp.ndarray, 
              state: jnp.ndarray,
              d_rates: jnp.ndarray = 1,
              transpose: bool = False,
              ) -> jnp.ndarray:
    """This computes R^{-1} x = (I - Q D^{-1})^{-1} x

    Args:
        log_theta (np.ndarray): Log values of the theta matrix
        x (np.ndarray): Vector to multiply with from the right. Length must equal the number of
            nonzero entries in the state vector.
        state (np.ndarray): Binary state vector, representing the current sample's events.
        transpose (bool): Logical flag, if true calculate x^T (I - Q D^{-1})^{-1}

    Returns:
        np.ndarray: R_i^{-1} x or x^T R_i^{-1}
    """
    state_size = jnp.log2(x.shape[0]).astype(int)

    lidg = -1 / (kron_diag(log_theta=log_theta,
                 state=state, diag=jnp.ones_like(x))-d_rates)
    y = lidg * x

    y = lax.fori_loop(
        lower=0,
        upper=state_size+1,
        body_fun=lambda _, val: lidg * (kronvec(log_theta=log_theta, p=val,
                                                state=state, diag=False, transpose=transpose) + x),
        init_val=y
    )

    return y


@jit
def x_partial_Q_y(
        log_theta: jnp.ndarray,
        x: jnp.ndarray,
        y: jnp.ndarray,
        state: jnp.ndarray, 
        ) -> jnp.ndarray:
    """This function computes x \partial Q y with \partial Q the Jacobian of Q w.r.t. all thetas
    efficiently using the shuffle trick (sic!).

    Args:
        log_theta (np.ndarray): Logarithmic theta values of the MHN
        x (np.ndarray): x vector to multiply with from the left. Length must equal the number of
            nonzero entries in the state vector.
        y (np.ndarray): y vector to multiply with from the right. Length must equal the number of
            nonzero entries in the state vector.
        state (np.ndarray): Binary state vector, representing the current sample's events.

    Returns:
        np.ndarray: x \partial_(\Theta_{ij}) Q y for i, j = 1, ..., n+1
    """
    n = log_theta.shape[0]
    val = jnp.zeros(shape=(n, n))

    def body_fun(i, val):

        z = x * kronvec_i(log_theta=log_theta,
                          p=y, i=i, state=state)

        def body_fun(j, val):

            z, _val = lax.switch(
                state[j],
                [
                    lambda x: (x, 0.),
                    lambda x: f(x)
                ],
                val[0],

            )
            return z, val[1].at[j].set(_val)

        z, val = lax.fori_loop(
            lower=0,
            upper=i,
            body_fun=body_fun,
            init_val=(z, val)
        )

        z, _val = lax.switch(
            state[i],
            [
                lambda z: (z, z.sum()),
                lambda z: t(z)
            ],
            z,
        )
        val = val.at[i].set(_val)

        z, val = lax.fori_loop(
            lower=i+1,
            upper=n,
            body_fun=body_fun,
            init_val=(z, val)
        )

        return val

    val = vmap(body_fun, in_axes=(0, 0), out_axes=0)(
        jnp.arange(n, dtype=int), val)
    d_diag = -jnp.sum(val, axis=0) + jnp.diagonal(val)
    return val, d_diag


@jit
def gradient(log_theta: jnp.ndarray,
             state: jnp.ndarray, 
             p_0: jnp.ndarray
             ) -> jnp.ndarray:
    """This computes the gradient of the score function, which is the log-likelihood of a data vector p_D
    with respect to the log_theta matrix

    Args:
        log_theta (np.ndarray): Theta matrix with logarithmic entries.
        state (np.ndarray): Binary state vector, representing the current sample's events.
        p_0 (np.ndarray): Starting distribution

    Returns:
        jnp.ndarray: \partial_theta (p_D^T log p_theta)
    """
    p_theta = R_inv_vec(log_theta=log_theta, x=p_0, state=state)
    x = jnp.zeros_like(p_theta)
    x = x.at[-1].set(1/p_theta[-1])
    x = R_inv_vec(log_theta=log_theta, x=x,
                  state=state, transpose=True)
    d_th, d_diag = x_partial_Q_y(log_theta=log_theta, x=x, y=p_theta, state=state)
    return d_th, d_diag, p_theta