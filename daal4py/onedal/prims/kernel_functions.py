# ===============================================================================
# Copyright 2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

import numpy as np
from daal4py.onedal.common import _check_array

def linear_kernel(X, Y=None, scale=1.0, shift=0.0):
    # TODO
    from _onedal4py_host import PyLinearKernelParams, PyLinearKernelCompute

    X = _check_array(X, dtype=[np.float64, np.float32], force_all_finite=False)
    if Y is None:
        Y = X
    else:
        Y = _check_array(Y, dtype=[np.float64, np.float32], force_all_finite=False)

    _onedal_params = PyLinearKernelParams(scale, shift)
    c_kernel = PyLinearKernelCompute(_onedal_params)
    c_kernel.compute(X, Y)
    return c_kernel.get_values()

def rbf_kernel(X, Y=None, gamma=None):
    """
    Compute the rbf (gaussian) kernel between X and Y::

        K(x, y) = exp(-gamma ||x-y||^2)

    for each pair of rows x in X and y in Y.

    Parameters
    ----------
    X : ndarray of shape (n_samples_X, n_features)

    Y : ndarray of shape (n_samples_Y, n_features)

    gamma : float, default=None
        If None, defaults to 1.0 / n_features.

    Returns
    -------
    kernel_matrix : ndarray of shape (n_samples_X, n_samples_Y)
    """
    from _onedal4py_host import PyRbfKernelParams, PyRbfKernelCompute

    X = _check_array(X, dtype=[np.float64, np.float32], force_all_finite=False)
    if Y is None:
        Y = X
    else:
        Y = _check_array(Y, dtype=[np.float64, np.float32], force_all_finite=False)

    if gamma is None:
        gamma = 1.0 / X.shape[1]

    sigma = np.sqrt(0.5 / gamma)
    _onedal_params = PyRbfKernelParams(sigma=sigma)
    c_kernel = PyRbfKernelCompute(_onedal_params)
    c_kernel.compute(X, Y)
    return c_kernel.get_values()

def poly_kernel(X, Y, scale=1.0, shift=0.0, degree=3):
    # TODO
    from _onedal4py_host import PyLinearKernelParams, PyLinearKernelCompute

    X = _check_array(X, dtype=[np.float64, np.float32], force_all_finite=False)
    Y = _check_array(Y, dtype=[np.float64, np.float32], force_all_finite=False)

    _onedal_params = PyLinearKernelParams(scale=scale, shift=shift, degree=degree)
    c_kernel = PyLinearKernelCompute(_onedal_params)
    c_kernel.compute(X, Y)
    return c_kernel.get_values()

