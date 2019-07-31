#!/usr/bin/env python2

from pydrake.all import *
from helpers import RPYValkyrieFixedPointState, RPYValkyrieFixedPointTorque
from controllers import ValkyrieController
import numpy as np

# Load the valkyrie model from a urdf file
robot_description_file = "drake/examples/valkyrie/urdf/urdf/valkyrie_A_sim_drake_one_neck_dof_wide_ankle_rom.urdf"
robot_urdf = FindResourceOrThrow(robot_description_file)
builder = DiagramBuilder()
scene_graph = builder.AddSystem(SceneGraph())
robot = builder.AddSystem(MultibodyPlant(time_step=0))   # 0 for continuous, dt for discrete
robot.RegisterAsSourceForSceneGraph(scene_graph)
Parser(plant=robot).AddModelFromFile(robot_urdf)

# Add a flat ground with friction
X_BG = RigidTransform()
surface_friction = CoulombFriction(
        static_friction = 0.7,
        dynamic_friction = 0.1)
robot.RegisterCollisionGeometry(
        robot.world_body(),      # the body for which this object is registered
        X_BG,                    # The fixed pose of the geometry frame G in the body frame B
        HalfSpace(),             # Defines the geometry of the object
        "ground_collision",      # A name
        surface_friction)        # Coulomb friction coefficients
robot.RegisterVisualGeometry(
        robot.world_body(),
        X_BG,
        HalfSpace(),
        "ground_visual",
        np.array([0.5,0.5,0.5,0.7]))    # Color

robot.Finalize()
assert robot.geometry_source_is_registered()

# Set up the Scene Graph
builder.Connect(
        scene_graph.get_query_output_port(),
        robot.get_geometry_query_input_port())
builder.Connect(
        robot.get_geometry_poses_output_port(),
        scene_graph.get_source_pose_port(robot.get_source_id()))

# Connect the visualizer
ConnectDrakeVisualizer(builder=builder, scene_graph=scene_graph)
diagram = builder.Build()

diagram_context = diagram.CreateDefaultContext()
robot_context = diagram.GetMutableSubsystemContext(robot, diagram_context)

# Send fixed commands of zero to the joints
zero_cmd = np.zeros(robot.num_actuators())
robot_context.FixInputPort(
        robot.get_actuation_input_port().get_index(), 
        np.zeros(30)+0.5)


# Simulator setup
simulator = Simulator(diagram, diagram_context)
simulator.set_target_realtime_rate(1.0)
simulator.set_publish_every_time_step(False)

# Set initial state
state = robot_context.get_mutable_continuous_state_vector()
initial_state_vec = np.zeros(robot.num_positions()+robot.num_velocities())
initial_state_vec[0] = 1
initial_state_vec[6] = 1.2
#initial_state_vec = RPYValkyrieFixedPointState()  # computes [q,qd] for a reasonable starting position
state.SetFromVector(initial_state_vec)

# Use a different integrator to speed up simulation (default is RK3)
integrator = RungeKutta2Integrator(diagram, 5e-4, diagram_context)
simulator.reset_integrator(integrator)

# Run the simulation
simulator.Initialize()
simulator.AdvanceTo(1.0)
