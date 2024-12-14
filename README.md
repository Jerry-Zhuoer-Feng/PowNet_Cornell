# PowNet_Cornell
A high spatial-temporal resolution unit commitment/economic dispatch model for the electricity supply-transmission-demand system of Cornell’s Ithaca campus.

The model is a mixed integer linear programming problem (MILP), which is non-convex by definition but can be solved by solvers such as Gurobi, which is what we used. We developed the solver of this model based on an Academic Web License Service (WLS) License for Gurobi. We chose Gurobi due to its fast performance and the fact that other solvers such as CPLEX Community Edition is limited to 1,000 variables, for which our model exceeds.

The model is set up in Python 3.9 with the Pyomo optimization package, and is broken down into three files. *pownet_datasetup.py* creates a model instance in the format of a .dat file from the input files, which will then be fed to *pownet_solver.py*, together with the mathematical formulation of the model, *pownet_model.py*. The model can be run either from terminal or in the provided wrapper named *Wrapper.ipynb*. The subsequent analysis and the reproduction of the generation mix, operating costs, and plots can be found in *analysis_genmix_cost_emi.ipynb*. The input data consists of 6 .csv files that correspond to operational parameters of dispatchable units, derate factors (defaulted to 1), available hydroelectric power, available solar power, transmission network, and demand.

We crafted 6 scenarios plus the current infrastructure set up:
0. Current: Existing Infrastructure without Hydrogen/Geothermal
1. Business-as-Usual (BaU): Existing Infrastructure + Hydrogen/Geothermal with real life data or best estimates
2. Oil & Gas Crisis: Natural gas price + 400%
3. Social Cost of CO2: Fuel Price + Social Cost of Carbon @ $185 per ton of CO2 (Rennert, K. et al. *Nature*. 2022)
4. Aggresive Solar: NY Large Scale Renewable Energy (LSRE) fully online @ 110 MW, all electricity go to Cornell
5. More Boreholes: Geothermal Potential + 200%
