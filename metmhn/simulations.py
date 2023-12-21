import numpy as np
from numpy.typing import ArrayLike
from metmhn.jx.kronvec import diagnosis_theta


def single_traject(
        log_theta: ArrayLike,
        t_obs: float,
        fd_effects: ArrayLike,
        prim: ArrayLike = None,
        met: ArrayLike = None,
        rng: np.random.Generator = None
) -> tuple[np.array, np.array, np.array, np.array, np.array]:
    """This function models the trajectory of a single tumor and metastasis starting from 
    given states of the primary tumor and the metastasis until a given time.

    Args:
        log_theta (ArrayLike): Logarithmic values of the Theta matrix. 
        t_obs (float): Time of observation.
        prim (ArrayLike, shape (n+1,)): Initial state of the primary tumor. Binary.
        met (ArrayLike, shape (n+1,)): Initial state of the metastasis. Binary.
        rng (np.random.Generator, optional): Random number generator. Defaults to None.

    Returns:
        tuple[ArrayLike, ArrayLike, ArrayLike, ArrayLike, ArrayLike]: 
         - state of the primary tumor
         - state of the metastasis
         - events that happened before the seeding (binary)
         - order of events in the PT
         - order of Events in the MT
    """
    n = log_theta.shape[0]
    b_rates = np.diag(log_theta)
    log_theta_prim = log_theta.copy()
    log_theta_prim[:-1, -1] = -fd_effects[-1]
    if prim is None and met is None:
        prim, met = np.zeros(n), np.zeros(n)
    elif not (prim is not None and met is not None):
        raise ValueError("prim and met must be either both known or both None")

    pre_seeding_events = np.zeros_like(prim)
    j_prim, j_met = int(prim.sum()), int(met.sum())
    t = 0.
    inds = np.arange(0, 2*n, dtype=int)
    order_pt, order_mt = np.zeros((n, n)), np.zeros((n, n))
    while True:
        # Seeding didn't happen yet
        if prim[-1] == 0:
            rates = np.exp(log_theta_prim @ prim + b_rates)
            rates[prim == 1] = 0.
            out_rate = np.sum(rates)
            t += rng.exponential(scale=1/out_rate, size=1)
            if (t >= t_obs):
                break
            else:
                next_event = rng.choice(inds[:n], size=1, p=rates/out_rate)
                prim[next_event], met[next_event] = 1, 1
                pre_seeding_events[next_event] = 1
                order_pt[j_prim, next_event], order_mt[j_met, next_event] = 1, 1
                j_prim += 1
                j_met += 1

        # Seeding already happened
        else:
            prim_rates = np.exp(log_theta_prim @ prim + b_rates)
            prim_rates[prim == 1] = 0.
            met_rates = np.exp(log_theta @ met + b_rates)
            met_rates[met == 1] = 0.
            out_rate = np.sum(prim_rates) + np.sum(met_rates)
            t += rng.exponential(scale=1/out_rate, size=1)
            if(t >= t_obs):
                break
            else:
                next_event = rng.choice(inds,
                                        size=1,
                                        p=np.concatenate((prim_rates, met_rates))/out_rate)
                if next_event >= n:
                    met[next_event - n] = 1
                    order_mt[j_met, next_event-n] = 1
                    j_met += 1
                else:
                    prim[next_event] = 1
                    order_pt[j_prim, next_event] = 1
                    j_prim += 1
    return prim, met, pre_seeding_events, order_pt, order_mt


def single_traject_timed(
        log_theta: ArrayLike,
        t_obs: float,
        initial: ArrayLike = None,
        rng: np.random.Generator = None
) -> np.array:
    """This function models the trajectory of a single tumor and metastasis starting from 
    given states of the primary tumor and the metastasis until a given time.

    Args:
        log_theta (ArrayLike): Logarithmic values of the Theta matrix. 
        t_obs (float): Time of observation. May be infinity.
        state (ArrayLike, shape (n+1,)): Initial state of the primary tumor and metastasis. Binary.
        rng (np.random.Generator, optional): Random number generator. Defaults to None.

    Returns:
        np.array, shape (2n+1,): Accumulation times of the events. -1 if there were present
        at the start of the simulation already  
    """
    n = log_theta.shape[0]
    b_rates = np.diag(log_theta)
    log_theta_prim = log_theta.copy()
    log_theta_prim[0: -1, -1] = 0.0
    rng = rng or np.random.default_rng(42)

    if initial is None:
        initial = np.zeros(2*n-1)

    prim_final = initial[::2].astype(float)
    met_final = initial[list(range(1, 2 * n - 1, 2)) + [-1]].astype(float)

    prim = prim_final.astype(int)
    met = met_final.astype(int)

    prim_final *= -1
    met_final *= -1

    t = 0.
    inds = np.arange(0, 2*n, dtype=int)

    while not prim.all() or not met.all():
        # Seeding didn't happen yet
        if prim[-1] == 0:
            rates = np.exp(log_theta @ prim + b_rates)
            rates[prim == 1] = 0.
            out_rate = np.sum(rates)
            t += rng.exponential(scale=1/out_rate, size=1)
            if (t >= t_obs):
                break
            next_event = rng.choice(inds[:n], size=1, p=rates/out_rate)
            prim[next_event], met[next_event] = 1, 1
            prim_final[next_event], met_final[next_event] = t, t
        # Seeding already happened
        else:
            prim_rates = np.exp(log_theta_prim @ prim + b_rates)
            prim_rates[prim == 1] = 0.
            met_rates = np.exp(log_theta @ met + b_rates)
            met_rates[met == 1] = 0.
            out_rate = np.sum(prim_rates) + np.sum(met_rates)
            t += rng.exponential(scale=1/out_rate, size=1)
            if(t >= t_obs):
                break
            next_event = rng.choice(inds,
                                    size=1,
                                    p=np.concatenate((prim_rates, met_rates))/out_rate)
            if next_event >= n:
                met[next_event - n] = 1
                met_final[next_event - n] = t
            else:
                prim[next_event] = 1
                prim_final[next_event] = t
    state = np.concatenate((prim_final[:-1], met_final))
    return np.concatenate((state[:-1].reshape(2, n-1).flatten(order="F"), state[[-1]]))


def sample_metmhn(
        log_theta_fd: ArrayLike,
        log_theta_sd: ArrayLike,
        fd_effects: ArrayLike,
        sd_effects: ArrayLike,
        rng: np.random.Generator = None
) -> tuple[ArrayLike, float, ArrayLike, ArrayLike, ArrayLike]:
    """This function samples from the metMHN, returning all events
    that happened before the seeding

    Args:
        log_theta (ArrayLike): Logarithmic values of the Theta matrix.
        rng (np.random.Generator, optional): Random number generator. Defaults to None.

    Returns:
        tuple[ArrayLike, float, ArrayLike, ArrayLike, ArrayLike]:
         - PT-MT sample from metMHN
         - Events that happened prior to the seeding
         - Order of mutations in the PT
         - Order of mutations in the MT
    """
    t_1 = rng.exponential(scale=1, size=1)
    t_2 = rng.exponential(scale=1, size=1)
    # Simulate until 1st diagnosis
    prim, met, pre_seeding_events, order_pt, order_mt = single_traject(
        log_theta=log_theta_fd, t_obs=t_1, fd_effects=fd_effects, rng=rng)
    # Record the state of the primary at 1st diagnosis
    prim_obs = prim.copy()
    met_obs = met.copy()
    # Simulate until 2nd diagnosis, if the seeding happened
    if prim[-1] == 1:
        # Record only the state of the met at 2nd diagnosis
        _, met_obs, _, _, order_mt_ps = single_traject(
            log_theta=log_theta_sd, t_obs=t_2, 
            fd_effects=sd_effects, prim=prim, 
            met=met,  rng=rng)
        order_mt += order_mt_ps
    # Concatenate the prim and met in the shape metMHN expects
    return np.vstack((prim_obs, met_obs)).flatten(order="F")[:-1], pre_seeding_events, order_pt, order_mt


def simulate_dat(
    theta_in: ArrayLike,
    fd_effects: ArrayLike,
    sd_effects: ArrayLike,
    n_dat: int,
    rng: np.random.Generator = None
) -> tuple[np.array, np.array, np.array]:
    """ Simulate a dataset of n_dat observations from metMHN

    Args:
        theta_in (ArrayLike): Thetamatrix with logarithmic entries
        fd_effects (ArrayLike): Effects of mutations in the PT on the rate of first diagnosis
        sd_effcets (ArrayLike): Effects of mutations int the MT on the rate of second diagnosis
        n_dat (int): Number of samples to generate
        rng (np.random.Generator, optional): _description_. Defaults to None.

    Returns:
        tuple[np.array, np.array, np.array]: Dataset of observations, Probability that a mutation happened prior to the seeding
    """
    n = theta_in.shape[0]
    dat = np.zeros((n_dat, 2*n-1))
    pre_seeding_probs = np.zeros(n)
    theta_fd = np.array(diagnosis_theta(theta_in, fd_effects))
    theta_sd = np.array(diagnosis_theta(theta_in, sd_effects))
    i = 0
    while i < n_dat:
        datum, psp, _, _= sample_metmhn(theta_fd, theta_sd, fd_effects, sd_effects, rng)
        dat[i, :] = datum
        pre_seeding_probs += psp
        i += 1

    dat = dat.astype(int)
    return dat, pre_seeding_probs/n_dat


def p_shared_mut_pre_seed(theta, fd_effects, sd_effects, n_dat, rng):
    theta_fd = np.array(diagnosis_theta(theta, fd_effects))
    theta_sd = np.array(diagnosis_theta(theta, sd_effects))
    n = theta.shape[0]
    pre_seeded_muts = np.zeros(n-1)
    total_muts = np.zeros(n-1)
    i = 0
    while i < n_dat:
        datum, psp, _, _ = sample_metmhn(theta_fd, theta_sd, fd_effects, sd_effects, rng)
        if datum[-1] == 1:
            both = (datum[:-1:2]+datum[1::2]==2)
            pre_seeded_muts += psp[:-1] * both
            total_muts += both
            i += 1
    return pre_seeded_muts, total_muts 


def p_any_mut_pre_seed(theta, fd_effects, sd_effects, n_dat, rng):
    theta_fd = np.array(diagnosis_theta(theta, fd_effects))
    theta_sd = np.array(diagnosis_theta(theta, sd_effects))
    n = theta.shape[0]
    pre_seeded_muts = np.zeros(n-1)
    total_muts_prim = np.zeros(n-1)
    total_muts_met = np.zeros(n-1)
    i = 0
    while i < n_dat:
        datum, psp, _, _ = sample_metmhn(theta_fd, theta_sd, fd_effects, sd_effects, rng)
        if datum[-1] == 1:
            pre_seeded_muts += psp[:-1]
            total_muts_prim += datum[:-1:2]
            total_muts_met +=  datum[1::2]
            i += 1
             
    return pre_seeded_muts, total_muts_prim, total_muts_met


def p_full_orders(theta, fd_effects, sd_effects, n_dat, rng):
    theta_fd = np.array(diagnosis_theta(theta, fd_effects))
    theta_sd = np.array(diagnosis_theta(theta, sd_effects))
    n = theta.shape[0]
    prim_muts = np.zeros((n, n))
    total_prims = np.zeros(n)
    met_muts = np.zeros((n, n))
    total_mets = np.zeros(n)
    i = 0
    while i < n_dat:
        datum, _, full_prim, full_met = sample_metmhn(
            theta_fd, theta_sd, fd_effects, sd_effects, rng)
        if datum[-1] == 1:
            prim_muts += full_prim
            met_muts += full_met
            total_prims += datum[::2]
            total_mets += np.concatenate((datum[1::2], np.array([1])))
            i += 1
    return prim_muts/total_prims, met_muts/total_mets