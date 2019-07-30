#!/usr/bin/env python2

from pydrake.all import *
from helpers import RPYValkyrieFixedPointState, RPYValkyrieFixedPointTorque
from controllers import ValkyrieController
import numpy as np

# Load the model from a urdf file
robot_description_file = "drake/examples/valkyrie/urdf/urdf/valkyrie_A_sim_drake_one_neck_dof_wide_ankle_rom.urdf"
robot_urdf = FindResourceOrThrow(robot_description_file)
tree = RigidBodyTree(robot_urdf, FloatingBaseType.kRollPitchYaw)

AddFlatTerrainToWorld(tree, 100, 10)  # add some flat terrain to walk on

# See some model parameters
print(tree.get_num_positions())
print(tree.get_num_velocities())
print(tree.get_num_actuators())
print(tree.get_num_bodies())
print("")

# Get equations of motion for given q, qd
q = np.zeros(tree.get_num_positions())
qd = np.zeros(tree.get_num_velocities())
cache = tree.doKinematics(q,qd)

bodies = [tree.get_body(j) for j in range(tree.get_num_bodies())]
no_wrench = { body : np.zeros(6) for body in bodies}

C = tree.dynamicsBiasTerm(cache, no_wrench)  # correolis and centripedal terms
H = tree.massMatrix(cache)                   # mass matrix

print(C.shape)
print(H.shape)

# Centroidal momentum quantities
A = tree.centroidalMomentumMatrix(cache)
Ad_qd = tree.centroidalMomentumMatrixDotTimesV(cache)
print(A.shape)
print(Ad_qd.shape)

# Simulation setup
builder = DiagramBuilder()
lc = DrakeLcm()
robot = builder.AddSystem(RigidBodyPlant(tree))
visualizer_publisher = builder.AddSystem(DrakeVisualizer(tree,lc))
builder.Connect(robot.get_output_port(0), visualizer_publisher.get_input_port(0))

# Apply constant torques to the joints
#tau_vec = np.zeros(tree.get_num_actuators())
#force = builder.AddSystem(ConstantVectorSource(tau_vec))
#builder.Connect(force.get_output_port(0), robot.get_input_port(0))
controller = builder.AddSystem(ValkyrieController())
builder.Connect(controller.get_output_port(0), robot.get_input_port(0))
builder.Connect(robot.get_output_port(0),controller.get_input_port(0))

diagram = builder.Build()
simulator = Simulator(diagram)
simulator.set_target_realtime_rate(1.0)
simulator.set_publish_every_time_step(False)
context = simulator.get_mutable_context()

# Set initial state
state = context.get_mutable_continuous_state_vector()
initial_state_vec = RPYValkyrieFixedPointState()  # computes [q,qd] for a reasonable starting position
state.SetFromVector(initial_state_vec)

# Use a different integrator to speed up simulation (default is RK3)
integrator = RungeKutta2Integrator(diagram, 1e-3, context)
simulator.reset_integrator(integrator)

# Run the simulation
simulator.Initialize()
simulator.AdvanceTo(1.0)