import os
os.environ['CUDA_VISIBLE_DEVICES']= str(int(os.environ['OMPI_COMM_WORLD_LOCAL_RANK']) % 4)
from mpi4py import MPI
import numpy as np
import matplotlib.pyplot as plt
from dask_mpi import initialize
initialize()
from dask.distributed import Client

import hoomd
import hoomd.md as md
import hoomd.dlext
import pysages
from pysages.collective_variables import Component
from pysages.methods import HarmonicBias, HistogramLogger

def plot(xi_hist, target_hist, lim):
    fig, ax = plt.subplots()

    ax.set_xlabel(r"CV $\xi_i$")
    ax.set_ylabel(r"$p(\xi_i)$")

    x = np.linspace(lim[0], lim[1], xi_hist[0].shape[0])

    for i in range(len(xi_hist)):
        line, = ax.plot(x, xi_hist[i], label="i= {0}".format(i))
        ax.plot(x, target_hist[i], "--", color=line.get_color())

    ax.legend(loc="best")
    fig.savefig("hist.pdf")
    plt.close(fig)


def validate_hist(xi_hist, target, epsilon=0.1):
    assert len(xi_hist) == len(target)
    for i in range(len(xi_hist)):
        val = np.sqrt(np.mean((xi_hist[i]-target[i])**2))
        if val > epsilon:
            raise RuntimeError("Biased historgram deviation too large: {0} epsilon {1}".format(val, epsilon))


def get_target_dist(center, k, lim, bins):
    x = np.linspace(lim[0], lim[1], bins)
    p = np.exp(-0.5*k*(x-center)**2)
    # norm numerically
    p *= (lim[1]-lim[0])/np.sum(p)
    return p


def generate_context(**kwargs):
    context = hoomd.context.SimulationContext()
    with context:
        system = hoomd.init.read_gsd("start.gsd")
        hoomd.md.integrate.nve(group=hoomd.group.all())
        hoomd.md.integrate.mode_standard(dt=0.01)

        nl = hoomd.md.nlist.cell()
        dpd = hoomd.md.pair.dpd(r_cut=1,nlist=nl,seed=42,kT=1.)
        dpd.pair_coeff.set("A","A",A=kwargs.get("A", 5.),gamma=kwargs.get("gamma", 1.))
    return context


def run_sim(j):
    comm_world = MPI.COMM_WORLD
    comm_self = MPI.COMM_SELF
    rank = comm_world.Get_rank()

    hoomd.context.initialize(mpi_comm=comm_self)
    cvs = [Component([0], 2),]
    cvs += [Component([0], 1),]
    cvs += [Component([0], 0),]

    center_cv = [ 0.,]
    center_cv += [0.3, -0.3]

    k= 15
    method = HarmonicBias(cvs, k, center_cv)
    callback = HistogramLogger(100)

    method.run(generate_context, int(1e5), callback, {"A":7.}, profile=True)

    # Lmax = np.max([system.box.Lx, system.box.Ly, system.box.Lz])
    Lmax = 5.
    bins = 25
    target_hist = []
    for i in range(len(center_cv)):
        target_hist.append(get_target_dist(center_cv[i], k, (-Lmax/2, Lmax/2), bins))

    lims = [(-Lmax/2, Lmax/2) for i in range(3)]
    hist, edges = callback.get_histograms(bins=bins, range=lims)
    hist_list = [ np.sum(hist, axis=(1,2))/(Lmax**2),
                  np.sum(hist, axis=(0,2))/(Lmax**2),
                  np.sum(hist, axis=(0,1))/(Lmax**2),
                 ]
    return hist_list, target_hist


if __name__ == "__main__":
    client = Client()

    futures = client.map(run_sim, range(2))
    results = client.gather(futures)
    for hist_list, target_hist in results:
        validate_hist(hist_list, target_hist)
