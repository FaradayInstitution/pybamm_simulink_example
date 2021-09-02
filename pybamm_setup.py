# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 15:53:32 2020

@author: tom
"""


import pybamm
#import matplotlib.pyplot as plt
import numpy as np
from scipy import io
import os
import shutil
import casadi
import pandas as pd
import pickle
from scipy.interpolate import interp1d


def main(plot=False):
    settings = pd.read_csv('settings.csv').to_dict(orient='index')[0]
    dt = settings['dt']
    h = settings['cooling_coefficient']
    T_ref = settings['reference_temperature']
    soc_init_top = settings['soc_init_top']
    soc_init_bottom = settings['soc_init_bottom']
    I_app = 2.0
    chemistry = pybamm.parameter_sets.Chen2020
    parameter_values = pybamm.ParameterValues(chemistry=chemistry)
    model_options = {
        "thermal": "lumped",
        "external submodels": ["thermal"],
    }
    cell_rad = settings['battery_radius']
    cell_height = settings['battery_height']
    cell_width = settings['battery_width']
    area_circ = np.pi*cell_rad**2
    area_cyl = 2*np.pi*cell_rad*cell_height
    cool_area = 2*area_circ + area_cyl
    cell_vol = area_circ*cell_height
    model = pybamm.lithium_ion.SPMe(model_options)
    
    lower_voltage_cutoff = 2.6
    upper_voltage_cutoff = 4.2
    
    parameter_values.update({
        "Current function [A]": "[input]",
        "Lower voltage cut-off [V]": lower_voltage_cutoff,
        "Upper voltage cut-off [V]": upper_voltage_cutoff,
        "Electrode height [m]": cell_height,
        "Electrode width [m]": cell_width,
        "Cell volume [m3]": cell_vol,
        "Cell cooling surface area [m2]": cool_area,
        "Reference temperature [K]": T_ref,
        "Total heat transfer coefficient [W.m-2.K-1]": h,
        "Initial temperature [K]" : T_ref,
    })
    

    solver = pybamm.CasadiSolver(mode='safe')
    # make two simulations to solve with different initial SOC and generate y0
    sim = pybamm.Simulation(model, parameter_values=parameter_values, solver=solver)
    simb = pybamm.Simulation(model, parameter_values=parameter_values, solver=solver)

    inputs = {
        "Current function [A]": I_app,
        }
    external_variables = {"Volume-averaged cell temperature": 0.0}
    # Solve for very short time - we're just initialising here
    t_eval = np.linspace(0, 1e-6, 3)
    sim.solve(t_eval=t_eval, inputs=inputs, external_variables=external_variables,
              initial_soc=soc_init_top)
    simb.solve(t_eval=t_eval, inputs=inputs, external_variables=external_variables,
               initial_soc=soc_init_bottom)
    # Save the two inital states
    y0 = sim.solution.y.full()[:, 0]
    y0b = simb.solution.y.full()[:, 0]
    cwd = os.getcwd()
    temp_dir = os.path.join(cwd, 'temp')
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.mkdir(temp_dir)
    io.savemat(os.path.join(temp_dir, 'y0_top.mat'), {'y0':y0})
    io.savemat(os.path.join(temp_dir, 'y0_bot.mat'), {'y0':y0b})
    
    # Create integrator for specified time interval
    t_eval = np.linspace(0, dt, 11)
    t_eval_ndim = t_eval / sim.built_model.timescale.evaluate(inputs=inputs)
    inp_and_ext = inputs
    inp_and_ext.update(external_variables)
    casadi_integrator = solver.create_integrator(sim.built_model, inputs=inp_and_ext, t_eval=t_eval_ndim)
    # Save the integrator and variables function
    ci_path = os.path.join(temp_dir, 'integrator.casadi')
    casadi_integrator.save(ci_path)
    # These will be the outputs from the simulink class so must be changed there too
    variable_names = ['Terminal voltage [V]',
                      'Measured battery open circuit voltage [V]',
                      'X-averaged total heating [W.m-3]',
                      'X-averaged negative particle surface concentration [mol.m-3]',
                      'X-averaged positive particle surface concentration [mol.m-3]']
    ipo = ["Current function [A]"] # input parameter order
    casadi_objs = sim.built_model.export_casadi_objects(variable_names=variable_names,
                                                        input_parameter_order=ipo)
    variables = casadi_objs['variables']
    t, x, z, p = casadi_objs["t"], casadi_objs["x"], casadi_objs["z"], casadi_objs["inputs"]
    variables_stacked = casadi.vertcat(*variables.values())
    variables_fn = casadi.Function("variables", [t, x, z, p], [variables_stacked])
    v_path = os.path.join(temp_dir, 'variables.casadi')
    variables_fn.save(v_path)
    print('Casadi objects re-generated \n', os.listdir(temp_dir))
    print('When changing python script please restart Matlab for changes to take effect')
    
    if plot:
        # If testing run the simulation for longer and plot
        temp_parms = sim.built_model.submodels["thermal"].param
        Delta_T = parameter_values.process_symbol(temp_parms.Delta_T).evaluate(inputs=inputs)
        T_dim = 303
        T_non_dim = (T_dim - T_ref) / Delta_T
        external_variables = {"Volume-averaged cell temperature": T_non_dim}
        sim.solve(t_eval=np.linspace(0, 1800, 101), inputs=inputs, external_variables=external_variables)
        print("Initial neg concentration is : {}".format(sim.solution["X-averaged negative particle surface concentration [mol.m-3]"].entries[0]))
        print("Initial pos concentration is : {}".format(sim.solution["X-averaged positive particle surface concentration [mol.m-3]"].entries[0]))
        print("Initial Terminal voltage is : {}".format(sim.solution["Terminal voltage [V]"].entries[0]))

        # plot
        p = pybamm.QuickPlot(sim.solution, output_variables=variable_names)
        p.dynamic_plot()

if __name__ == '__main__':
    main(plot=True)
    