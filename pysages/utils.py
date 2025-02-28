# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2021: PySAGES contributors
# See LICENSE.md and CONTRIBUTORS.md at https://github.com/SSAGESLabs/PySAGES

from jax.tree_util import register_pytree_node
from plum import dispatch
from typing import Union

import jaxlib.xla_extension as xe


JaxArray = xe.DeviceArray
Bool = Union[JaxArray, bool]
Float = Union[JaxArray, float]
Int = Union[JaxArray, int]
Scalar = Union[None, bool, int, float]


class ToCPU:
    pass


# - https://github.com/google/jax/issues/446
# - https://github.com/google/jax/issues/806
def register_pytree_namedtuple(cls):
    register_pytree_node(
        cls,
        lambda xs: (tuple(xs), None),  # tell JAX how to unpack
        lambda _, xs: cls(*xs)         # tell JAX how to pack back
    )
    return cls


@dispatch
def copy(x: Scalar):
    return x


@dispatch(precedence = 1)
def copy(t: tuple, *args):
    return tuple(copy(x, *args) for x in t)


@dispatch
def copy(x: JaxArray):
    return x[:]


@dispatch
def copy(x, _: ToCPU):
    return copy(x)


@dispatch
def copy(x: JaxArray, _: ToCPU):
    return x.copy()


def identity(x):
    return x


# def wrap_around(boxsize, r):
#     half_boxsize = boxsize / 2
#     return np.mod(r + half_boxsize, boxsize) - half_boxsize
