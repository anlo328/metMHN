import numpy as np


def kronvec_sync(log_theta: np.array, p: np.array, i: int, n: int, state: np.array) -> np.array:
    """This computes the restricted version of the product of the synchronized part of the ith Q summand
    Q_i with a vector Q_i p.

    Args:
        log_theta (np.array): Log values of the theta matrix
        p (np.array): Vector to multiply with from the right. Length must equal the number of
        nonzero entries in the state vector.
        n (int): Total number of events in the MHN.
        state (np.array): Binary state vector, representing the current sample's events.

    Returns:
        np.array: _description_
    """
    y = p.copy()

    for j in range(n):

        mut = state[2 * j: 2 * j + 2]
        if mut.sum() == 0:
            if i == j:
                y *= -np.exp(log_theta[i, i])
        elif mut.sum() == 1:
            y = y.reshape((-1, 2), order="C")
            y[:, 1] = 0
            if i == j:
                y[:, 0] *= -np.exp(log_theta[i, i])
            y = y.flatten(order="F")
        else:
            y = y.reshape((-1, 4), order="C")
            y[:, 2:3] = 0
            if i == j:
                y[:, 0] *= -np.exp(log_theta[i, i])
                y[:, 3] = -1 * y[:, 0]
            else:
                y[:, 3] *= np.exp(log_theta[i, j])
            y = y.flatten(order="F")
    y = y.reshape((-1, 2), order="C")
    y[:, 1] = 0
    y = y.flatten(order="F")

    return y


def kronvec_prim(log_theta: np.array, p: np.array, i: int, n: int, state: np.array) -> np.array:

    y = p.copy()

    for j in range(n):

        mut = state[2 * j: 2 * j + 2]
        if mut.sum() == 0:
            if i == j:
                y *= -np.exp(log_theta[i, i])
        elif mut.sum() == 2:
            y = y.reshape((-1, 4), order="C")
            if i == j:
                theta = np.exp(log_theta[i, i])
                y[:, [0, 1]] = theta * y[:, 0]
                y[:, 0] *= -1
                y[:, [2, 3]] = theta * y[:, 2]
                y[:, 2] *= -1
            else:
                theta = np.exp(log_theta[i, j])
                y[:, 1] *= theta
                y[:, 3] *= theta
            y = y.flatten(order="F")
        else:
            y = y.reshape((-1, 2), order="C")
            if i == j:
                theta = np.exp(log_theta[i, i])
                y[:, 0] *= -theta
                if mut[0] == 1:
                    y[:, 1] = -y[:, 0]
                else:
                    y[:, 1] *= -theta
            else:
                if mut[0] == 1:
                    y[:, 1] *= np.exp(log_theta[i, j])
            y = y.flatten(order="F")
    y = y.reshape(-1, 2)
    y[:, 0] = 0
    y = y.flatten(order="F")

    return y


def kronvec_met(log_theta: np.array, p: np.array, i: int, n: int, state: np.array) -> np.array:

    y = p.copy()

    for j in range(n):

        mut = state[2 * j: 2 * j + 2]
        if mut.sum() == 0:
            if i == j:
                y *= -np.exp(log_theta[i, i])
        elif mut.sum() == 2:
            y = y.reshape((-1, 4), order="C")
            if i == j:
                theta = np.exp(log_theta[i, i])
                y[:, 0] *= -theta
                y[:, 1] *= -theta
                y[:, [2, 3]] = -1 * y[:, [0, 1]]
            else:
                theta = np.exp(log_theta[i, j])
                y[:, [2, 3]] *= theta
            y = y.flatten(order="F")
        else:
            y = y.reshape((-1, 2), order="C")
            if i == j:
                theta = np.exp(log_theta[i, i])
                y[:, 0] *= -theta
                if mut[1] == 1:
                    y[:, 1] = -y[:, 0]
                else:
                    y[:, 1] *= -theta
            else:
                if mut[1] == 1:
                    y[:, 1] *= np.exp(log_theta[i, j])
            y = y.flatten(order="F")
    y = y.reshape(-1, 2)
    y[:, 0] = 0
    y[:, 1] *= np.exp(log_theta[i, -1])
    y = y.flatten(order="F")

    return y


def kronvec_seed(log_theta: np.array, p: np.array, n: int, state: np.array) -> np.array:

    y = p.copy()

    for j in range(n):

        mut = state[2 * j: 2 * j + 2]
        if mut.sum() == 2:
            y = y.reshape((-1, 4), order="C")
            y[:, [1, 2]] = 0
            y[:, 3] *= -np.exp(log_theta[-1, j])
            y = y.flatten(order="F")
        elif mut.sum() == 1:
            y = y.reshape((-1, 2), order="C")
            y[:, 1] = 0
            y = y.flatten(order="F")
    y = y.reshape(-1, 2)
    y[:, 0] *= -np.exp(log_theta[-1, -1])
    y[:, 1] = -y[:, 0]
    y = y.flatten(order="F")

    return y
