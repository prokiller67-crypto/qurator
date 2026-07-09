"""Qurator — quantum optimization that picks your database indexes.

Pipeline: workload + candidates -> HypoPG Cost Probe -> index-selection problem
-> {classical baselines, QUBO -> QAOA} -> apply indexes -> measure real latency drop.
"""

__version__ = "0.1.0"
