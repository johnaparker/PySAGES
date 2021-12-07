# Environment
module load python/anaconda-2021.05 openmpi/4.1.1 cuda/11.5
source activate pysages

# Invoke mpirun with 2 extra processes
# Ranks 0,1 are dedicated to Dask server and scheduler
# Ranks 2+ are Dask workers
# map-by node: assigned processes to nodes in a round-robin fashion. This prevents configurations where multiple workers get assigned the same GPU
mpirun --map-by node -np 4 python harmonic_bias.py
