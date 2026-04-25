# Retrieval Eval Results

- Query count: 15
- Retrieval mode: hybrid
- Top-k per query: 5

## Query 1

- Query: What is the difference between ROS 2 discovery and QoS, and why do they matter for distributed robotics systems?
- Category: factual
- Retrieval mode: hybrid
- Routed intent: factual
- Preferred sources: ROS 2 official docs
- Preferred doc types: integration, concept, reference

### Rank 1

- Score: 0.4810
- Title: Discovery
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Discovery
- URL: https://docs.ros.org/en/jazzy/Concepts/Basic/About-Discovery.html
- Preview: # Discovery Discovery of nodes happens automatically through the underlying middleware of ROS 2. It can be summarized as follows: When a node is started, it advertises its presence to other nodes on the network with...

### Rank 2

- Score: 0.3328
- Title: uXRCE-DDS (PX4-ROS 2/DDS Bridge)
- Source: PX4 official docs
- Version: v1.16
- Section path: uXRCE-DDS (PX4-ROS 2/DDS Bridge) > PX4 ROS 2 QoS Settings
- URL: https://docs.px4.io/v1.16/en/middleware/uxrce_dds
- Preview: # uXRCE-DDS (PX4-ROS 2/DDS Bridge) ## PX4 ROS 2 QoS Settings PX4 QoS settings for publishers are incompatible with the default QoS settings for ROS 2 subscribers. So if ROS 2 code needs to subscribe to a uORB topic,...

### Rank 3

- Score: 0.3318
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Compatibility Issues > ROS 2 Subscriber QoS Settings
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Compatibility Issues ### ROS 2 Subscriber QoS Settings ROS 2 code that subscribes to topics published by PX4 must specify a appropriate (compatible) QoS setting in order to listen to topics....

### Rank 4

- Score: 0.2392
- Title: Installation
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Installation > Which install should you choose?
- URL: https://docs.ros.org/en/jazzy/Installation.html
- Preview: # Installation ## Which install should you choose? Installing from binary packages or from source will both result in a fully-functional and usable ROS 2 install. Differences between the options depend on what you...

### Rank 5

- Score: 0.2369
- Title: Using ros2doctor to identify issues
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Using ros2doctor to identify issues > When your ROS 2 setup is not running as expected, you can check its settings with the ros2doctor tool.
- URL: https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Getting-Started-With-Ros2doctor.html
- Preview: # Using ros2doctor to identify issues ## When your ROS 2 setup is not running as expected, you can check its settings with the ros2doctor tool. ros2doctor checks all aspects of ROS 2, including platform, version,...

## Query 2

- Query: What frame conventions differ between PX4 and ROS 2, and what conversions are needed when sending trajectory setpoints?
- Category: factual
- Retrieval mode: hybrid
- Routed intent: factual
- Preferred sources: PX4 official docs, ROS 2 official docs
- Preferred doc types: integration, concept, reference

### Rank 1

- Score: 0.4918
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Compatibility Issues > ROS 2 & PX4 Frame Conventions
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Compatibility Issues ### ROS 2 & PX4 Frame Conventions To rotate a vector from FLU to FRD a pi rotation around the X-axis (front) is sufficient. To rotate a vector from FRD to FLU a pi rotation...

### Rank 2

- Score: 0.4454
- Title: uXRCE-DDS (PX4-ROS 2/DDS Bridge)
- Source: PX4 official docs
- Version: v1.16
- Section path: uXRCE-DDS (PX4-ROS 2/DDS Bridge) > Fast-RTPS to uXRCE-DDS Migration Guidelines > Dependencies do not need to be removed > Topics no longer need to be synced between client and agent.
- URL: https://docs.px4.io/v1.16/en/middleware/uxrce_dds
- Preview: # uXRCE-DDS (PX4-ROS 2/DDS Bridge) ## Fast-RTPS to uXRCE-DDS Migration Guidelines ### Dependencies do not need to be removed #### Topics no longer need to be synced between client and agent. The list of bridged topics...

### Rank 3

- Score: 0.4028
- Title: ROS 2 Offboard Control Example
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 Offboard Control Example
- URL: https://docs.px4.io/v1.16/en/ros2/offboard_control
- Preview: # ROS 2 Offboard Control Example The following C++ example shows how to do position control in offboard mode from a ROS 2 node. The example starts sending setpoints, enters offboard mode, arms, ascends to 5 metres,...

### Rank 4

- Score: 0.3537
- Title: Simulation
- Source: PX4 official docs
- Version: v1.16
- Section path: Simulation > SITL Simulation Environment > Run Simulation Faster than Realtime
- URL: https://docs.px4.io/v1.16/en/simulation/
- Preview: # Simulation ## SITL Simulation Environment ### Run Simulation Faster than Realtime SITL can be run faster or slower than real-time when using Gazebo, Gazebo Classic, or jMAVSim. The speed factor is set using the...

### Rank 5

- Score: 0.2739
- Title: Basic Concepts
- Source: PX4 official docs
- Version: v1.16
- Section path: Basic Concepts > Drone Components & Parts > ESCs & Motors
- URL: https://docs.px4.io/v1.16/en/getting_started/px4_basic_concepts
- Preview: # Basic Concepts ## Drone Components & Parts ### ESCs & Motors Many PX4 drones use brushless motors that are driven by the flight controller via an Electronic Speed Controller (ESC) (the ESC converts a signal from the...

## Query 3

- Query: What is NITROS in Isaac ROS, and what problem is it trying to solve in accelerated ROS 2 pipelines?
- Category: factual
- Retrieval mode: hybrid
- Routed intent: factual
- Preferred sources: Isaac ROS docs, ROS 2 official docs
- Preferred doc types: concept, reference, integration

### Rank 1

- Score: 0.5123
- Title: CUDA with NITROS
- Source: Isaac ROS docs
- Version: latest
- Section path: CUDA with NITROS > Overview
- URL: https://nvidia-isaac-ros.github.io/concepts/nitros/cuda_with_nitros.html
- Preview: # CUDA with NITROS ## Overview CUDA is a parallel computing programming model and helps robotic applications to implement functions that would otherwise be too slow on a CPU. CUDA implemented in a ROS 2 node can take...

### Rank 2

- Score: 0.4811
- Title: Isaac for Manipulation Reference Architecture
- Source: Isaac ROS docs
- Version: latest
- Section path: Isaac for Manipulation Reference Architecture > What is NVIDIA Isaac for Manipulation?
- URL: https://nvidia-isaac-ros.github.io/reference_workflows/isaac_for_manipulation/reference_architecture.html
- Preview: # Isaac for Manipulation Reference Architecture ## What is NVIDIA Isaac for Manipulation? NVIDIA Isaac for Manipulation is a collection of GPU-accelerated libraries and Isaac ROS packages for perception-driven...

### Rank 3

- Score: 0.4427
- Title: Tutorial for NITROS Bridge with Isaac Sim
- Source: Isaac ROS docs
- Version: latest
- Section path: Tutorial for NITROS Bridge with Isaac Sim > Tutorial Walkthrough
- URL: https://nvidia-isaac-ros.github.io/concepts/nitros_bridge/tutorial_isaac_sim.html
- Preview: # Tutorial for NITROS Bridge with Isaac Sim ## Tutorial Walkthrough Clone isaac_ros_common repository under a new workspace: mkdir -p ~/isaac_sim_workspaces && \ cd ~/isaac_sim_workspaces && \ git clone -b release-4.3...

### Rank 4

- Score: 0.2718
- Title: Getting Started
- Source: Isaac ROS docs
- Version: latest
- Section path: Getting Started
- URL: https://nvidia-isaac-ros.github.io/getting_started/index.html
- Preview: # Getting Started Isaac ROS is a collection of NVIDIA® CUDA®-accelerated computing packages and AI models designed to streamline and expedite the development of advanced AI robotics applications. NVIDIA Isaac ROS is...

### Rank 5

- Score: 0.2554
- Title: isaac_ros_visual_slam
- Source: Isaac ROS docs
- Version: latest
- Section path: isaac_ros_visual_slam > Troubleshooting > Isaac ROS Troubleshooting
- URL: https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_visual_slam/isaac_ros_visual_slam/index.html
- Preview: # isaac_ros_visual_slam ## Troubleshooting ### Isaac ROS Troubleshooting For solutions to problems with Isaac ROS, please check here.

## Query 4

- Query: What are the main motion planning concepts in MoveIt, and how does the planning scene affect planning results?
- Category: factual
- Retrieval mode: hybrid
- Routed intent: factual
- Preferred sources: MoveIt docs
- Preferred doc types: concept, reference, integration

### Rank 1

- Score: 0.4320
- Title: Motion Planning
- Source: MoveIt docs
- Version: main
- Section path: Motion Planning > Motion planning adapters
- URL: https://moveit.picknik.ai/main/doc/concepts/motion_planning.html
- Preview: # Motion Planning ## Motion planning adapters The complete motion planning pipeline chains together a motion planner with other components called planning request adapters. Planning request adapters allow for pre-...

### Rank 2

- Score: 0.2996
- Title: MoveIt Quickstart in RViz
- Source: MoveIt docs
- Version: main
- Section path: MoveIt Quickstart in RViz > Step 4: Use Motion Planning with the Kinova Gen 3
- URL: https://moveit.picknik.ai/main/doc/tutorials/quickstart_in_rviz/quickstart_in_rviz_tutorial.html
- Preview: # MoveIt Quickstart in RViz ## Step 4: Use Motion Planning with the Kinova Gen 3 Now, you can start motion planning with the Kinova Gen 3 in the MoveIt RViz Plugin. Move the Start State to a desired location. Move the...

### Rank 3

- Score: 0.2543
- Title: Isaac for Manipulation Reference Architecture
- Source: Isaac ROS docs
- Version: latest
- Section path: Isaac for Manipulation Reference Architecture > Components > Component 2 - Nvblox for Environment and Obstacle Perception
- URL: https://nvidia-isaac-ros.github.io/reference_workflows/isaac_for_manipulation/reference_architecture.html
- Preview: # Isaac for Manipulation Reference Architecture ## Components ### Component 2 - Nvblox for Environment and Obstacle Perception This component provides a representation of the environment and obstacles in it for...

### Rank 4

- Score: 0.2362
- Title: Getting Started
- Source: MoveIt docs
- Version: main
- Section path: Getting Started > Next Step
- URL: https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html
- Preview: # Getting Started ## Next Step Nice job! Next, we will Visualize a robot with the interactive motion planning plugin for RViz

### Rank 5

- Score: 0.2230
- Title: MoveItCpp Tutorial
- Source: MoveIt docs
- Version: main
- Section path: MoveItCpp Tutorial > The Entire Code > Plan # 5
- URL: https://moveit.picknik.ai/main/doc/examples/moveit_cpp/moveitcpp_tutorial.html
- Preview: # MoveItCpp Tutorial ## The Entire Code ### Plan # 5 We can also generate motion plans around objects in the collision scene. First we create the collision object moveit_msgs::msg::CollisionObject collision_object;...

## Query 5

- Query: What safety actions can PX4 trigger when a failsafe event occurs, such as data link loss or geofence breach?
- Category: factual
- Retrieval mode: hybrid
- Routed intent: troubleshooting
- Preferred sources: PX4 official docs
- Preferred doc types: safety, troubleshooting, integration

### Rank 1

- Score: 0.6023
- Title: Safety (Failsafe) Configuration
- Source: PX4 official docs
- Version: v1.16
- Section path: Safety (Failsafe) Configuration > Data Link Loss Failsafe
- URL: https://docs.px4.io/v1.16/en/config/safety
- Preview: # Safety (Failsafe) Configuration ## Data Link Loss Failsafe The Data Link Loss failsafe is triggered if a telemetry link (connection to ground station) is lost. The settings and underlying parameters are shown below....

### Rank 2

- Score: 0.3525
- Title: Basic Concepts
- Source: PX4 official docs
- Version: v1.16
- Section path: Basic Concepts > Safety Settings (Failsafe)
- URL: https://docs.px4.io/v1.16/en/getting_started/px4_basic_concepts
- Preview: # Basic Concepts ## Safety Settings (Failsafe) PX4 has configurable failsafe systems to protect and recover your vehicle if something goes wrong! These allow you to specify areas and conditions under which you can...

### Rank 3

- Score: 0.2925
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Controlling a Vehicle
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Controlling a Vehicle To control applications, ROS 2 applications: - subscribe to (listen to) telemetry topics published by PX4 - publish to topics that cause PX4 to perform some action. The...

### Rank 4

- Score: 0.5418
- Title: Safety (Failsafe) Configuration
- Source: PX4 official docs
- Version: v1.16
- Section path: Safety (Failsafe) Configuration > Geofence Failsafe
- URL: https://docs.px4.io/v1.16/en/config/safety
- Preview: # Safety (Failsafe) Configuration ## Geofence Failsafe Geofence sourceGF_SOURCESet whether position source is estimated global position or direct from the GPS device. Preemptive geofence...

### Rank 5

- Score: 0.5408
- Title: Safety (Failsafe) Configuration
- Source: PX4 official docs
- Version: v1.16
- Section path: Safety (Failsafe) Configuration > Manual Control Loss Failsafe
- URL: https://docs.px4.io/v1.16/en/config/safety
- Preview: # Safety (Failsafe) Configuration ## Manual Control Loss Failsafe The manual control loss failsafe may be triggered if the connection to the RC transmitter or joystick is lost, and there is no fallback. If using an RC...

## Query 6

- Query: How do I install ROS 2 Jazzy on Ubuntu 24.04 and set up the environment for beginner tutorials?
- Category: procedural
- Retrieval mode: hybrid
- Routed intent: procedural
- Preferred sources: ROS 2 official docs
- Preferred doc types: getting_started, installation, tutorial

### Rank 1

- Score: 0.5099
- Title: Ubuntu (binary)
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Ubuntu (binary) > We currently support Ubuntu Noble (24.04) 64-bit x86 and 64-bit ARM. > If you are going to build ROS packages or otherwise do development, you can also install the development tools:
- URL: https://docs.ros.org/en/jazzy/Installation/Alternatives/Ubuntu-Install-Binary.html
- Preview: # Ubuntu (binary) ## We currently support Ubuntu Noble (24.04) 64-bit x86 and 64-bit ARM. ### If you are going to build ROS packages or otherwise do development, you can also install the development tools: $ sudo apt...

### Rank 2

- Score: 0.4799
- Title: Installation
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Installation > Building from source
- URL: https://docs.ros.org/en/jazzy/Installation.html
- Preview: # Installation ## Building from source We support building ROS 2 from source on the following platforms: Ubuntu Linux 24.04 Windows 10 RHEL-9/Fedora macOS

### Rank 3

- Score: 0.3386
- Title: Creating a workspace
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Creating a workspace
- URL: https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html
- Preview: # Creating a workspace Goal: Create a workspace and learn how to set up an overlay for development and testing. Tutorial level: Beginner Time: 20 minutes

### Rank 4

- Score: 0.3328
- Title: Getting Started
- Source: MoveIt docs
- Version: main
- Section path: Getting Started > Install ROS 2 and colcon
- URL: https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html
- Preview: # Getting Started ## Install ROS 2 and colcon MoveIt 2 currently supports multiple versions of ROS. Install whichever version you prefer. We primarily support ROS installed on Ubuntu 22.04 or 24.04 but other methods...

### Rank 5

- Score: 0.2847
- Title: Getting Started
- Source: Isaac ROS docs
- Version: latest
- Section path: Getting Started > System Requirements > ROS Support
- URL: https://nvidia-isaac-ros.github.io/getting_started/index.html
- Preview: # Getting Started ## System Requirements ### ROS Support All Isaac ROS packages are designed and tested to be compatible with ROS 2 Jazzy.

## Query 7

- Query: How do I create a ROS 2 workspace and build packages with colcon for a new project?
- Category: procedural
- Retrieval mode: hybrid
- Routed intent: procedural
- Preferred sources: ROS 2 official docs
- Preferred doc types: installation, tutorial, getting_started

### Rank 1

- Score: 0.5973
- Title: Creating a workspace
- Source: ROS 2 official docs
- Version: jazzy
- Section path: All required rosdeps installed successfully > In this tutorial, you sourced your main ROS 2 distro install as your underlay, and created an overlay by cloning and building packages in a new workspace.
- URL: https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html
- Preview: # Creating a workspace ## In this tutorial, you sourced your main ROS 2 distro install as your underlay, and created an overlay by cloning and building packages in a new workspace. The overlay gets prepended to the...

### Rank 2

- Score: 0.2986
- Title: Getting Started
- Source: MoveIt docs
- Version: main
- Section path: Getting Started > Create A Colcon Workspace and Download Tutorials
- URL: https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html
- Preview: # Getting Started ## Create A Colcon Workspace and Download Tutorials For tutorials you will need to have a colcon workspace setup. mkdir -p ~/ws_moveit/src

### Rank 3

- Score: 0.2980
- Title: Your First C++ MoveIt Project
- Source: MoveIt docs
- Version: main
- Section path: include <moveit/move_group_interface/move_group_interface.hpp> > 2.1 Build and Run
- URL: https://moveit.picknik.ai/main/doc/tutorials/your_first_project/your_first_project.html
- Preview: # Your First C++ MoveIt Project ## 2.1 Build and Run We will build and run the program to see that everything is right before we move on. Change the directory back to the workspace directory ws_moveit and run this...

### Rank 4

- Score: 0.2966
- Title: Getting Started
- Source: Isaac ROS docs
- Version: latest
- Section path: Getting Started > Create a Workspace
- URL: https://nvidia-isaac-ros.github.io/getting_started/index.html
- Preview: # Getting Started ## Create a Workspace x86 Platforms Create a ROS 2 workspace for experimenting with Isaac ROS: mkdir -p ~/workspaces/isaac_ros-dev/src echo 'export...

### Rank 5

- Score: 0.2028
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Installation & Setup > Build ROS 2 Workspace > Building the Workspace
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Installation & Setup ### Build ROS 2 Workspace #### Building the Workspace To create and build the workspace: Open a new terminal. Create and navigate into a new workspace directory using: INFO A...

## Query 8

- Query: How do I build PX4 from source and launch a simulator for the first validation run?
- Category: procedural
- Retrieval mode: hybrid
- Routed intent: procedural
- Preferred sources: PX4 official docs
- Preferred doc types: installation, tutorial, getting_started

### Rank 1

- Score: 0.5530
- Title: Building PX4 Software
- Source: PX4 official docs
- Version: v1.16
- Section path: Building PX4 Software > First Build (Using a Simulator)
- URL: https://docs.px4.io/v1.16/en/dev_setup/building_px4
- Preview: # Building PX4 Software ## First Build (Using a Simulator) First we'll build a simulated target using a console environment. This allows us to validate the system setup before moving on to real hardware and an IDE....

### Rank 2

- Score: 0.3774
- Title: uXRCE-DDS (PX4-ROS 2/DDS Bridge)
- Source: PX4 official docs
- Version: v1.16
- Section path: uXRCE-DDS (PX4-ROS 2/DDS Bridge) > Micro XRCE-DDS Agent Installation > Build/Run within ROS 2 Workspace
- URL: https://docs.px4.io/v1.16/en/middleware/uxrce_dds
- Preview: # uXRCE-DDS (PX4-ROS 2/DDS Bridge) ## Micro XRCE-DDS Agent Installation ### Build/Run within ROS 2 Workspace The agent can be built and launched within a ROS 2 workspace (or build standalone and launched from a...

### Rank 3

- Score: 0.3343
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Installation & Setup > Build ROS 2 Workspace > Running the Example
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Installation & Setup ### Build ROS 2 Workspace #### Running the Example To run the executables that you just built, you need to source local_setup.bash. This provides access to the "environment...

### Rank 4

- Score: 0.3328
- Title: Your First C++ MoveIt Project
- Source: MoveIt docs
- Version: main
- Section path: include <moveit/move_group_interface/move_group_interface.hpp> > 2.1 Build and Run > 3 Plan and Execute using MoveGroupInterface > 3.1 Build and Run
- URL: https://moveit.picknik.ai/main/doc/tutorials/your_first_project/your_first_project.html
- Preview: # Your First C++ MoveIt Project ## 2.1 Build and Run ### 3 Plan and Execute using MoveGroupInterface #### 3.1 Build and Run Just like before, we need to build the code before we can run it. In the workspace directory,...

### Rank 5

- Score: 0.3185
- Title: Simulation
- Source: PX4 official docs
- Version: v1.16
- Section path: Simulation > SITL Simulation Environment > Starting/Building SITL Simulation
- URL: https://docs.px4.io/v1.16/en/simulation/
- Preview: # Simulation ## SITL Simulation Environment ### Starting/Building SITL Simulation The build system makes it very easy to build and start PX4 on SITL, launch a simulator, and connect them. The syntax (simplified) looks...

## Query 9

- Query: How do I run the PX4 ROS 2 offboard control example from a new colcon workspace?
- Category: procedural
- Retrieval mode: hybrid
- Routed intent: procedural
- Preferred sources: PX4 official docs, ROS 2 official docs
- Preferred doc types: integration, installation, tutorial, getting_started

### Rank 1

- Score: 0.5682
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Installation & Setup > Build ROS 2 Workspace > Running the Example
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Installation & Setup ### Build ROS 2 Workspace #### Running the Example To run the executables that you just built, you need to source local_setup.bash. This provides access to the "environment...

### Rank 2

- Score: 0.5672
- Title: uXRCE-DDS (PX4-ROS 2/DDS Bridge)
- Source: PX4 official docs
- Version: v1.16
- Section path: uXRCE-DDS (PX4-ROS 2/DDS Bridge) > Micro XRCE-DDS Agent Installation > Build/Run within ROS 2 Workspace
- URL: https://docs.px4.io/v1.16/en/middleware/uxrce_dds
- Preview: # uXRCE-DDS (PX4-ROS 2/DDS Bridge) ## Micro XRCE-DDS Agent Installation ### Build/Run within ROS 2 Workspace The agent can be built and launched within a ROS 2 workspace (or build standalone and launched from a...

### Rank 3

- Score: 0.4920
- Title: ROS 2 Offboard Control Example
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 Offboard Control Example > Trying it out
- URL: https://docs.px4.io/v1.16/en/ros2/offboard_control
- Preview: # ROS 2 Offboard Control Example ## Trying it out Follow the instructions in ROS 2 User Guide to install PX and run the simulator, install ROS 2, and start the XRCE-DDS Agent. After that we can follow a similar set of...

### Rank 4

- Score: 0.4241
- Title: Creating a workspace
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Creating a workspace > A workspace is a directory containing ROS 2 packages. > Before building the workspace, you need to resolve the package dependencies.
- URL: https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html
- Preview: # Creating a workspace ## A workspace is a directory containing ROS 2 packages. ### Before building the workspace, you need to resolve the package dependencies. You may have all the dependencies already, but best...

### Rank 5

- Score: 0.2647
- Title: Basic Concepts
- Source: PX4 official docs
- Version: v1.16
- Section path: Basic Concepts > Flight Modes
- URL: https://docs.px4.io/v1.16/en/getting_started/px4_basic_concepts
- Preview: # Basic Concepts ## Flight Modes - Drive Modes (Differential Rover) - Drive Modes (Ackermann Rover) Instructions for how to set up your remote control switches to enable different flight modes is provided in Flight...

## Query 10

- Query: How do I set up Isaac ROS on a supported system and run an initial demo after environment setup?
- Category: procedural
- Retrieval mode: hybrid
- Routed intent: procedural
- Preferred sources: Isaac ROS docs
- Preferred doc types: installation, tutorial, getting_started

### Rank 1

- Score: 0.5120
- Title: Getting Started
- Source: Isaac ROS docs
- Version: latest
- Section path: Getting Started > Run an Isaac ROS Demo
- URL: https://nvidia-isaac-ros.github.io/getting_started/index.html
- Preview: # Getting Started ## Run an Isaac ROS Demo You’re now ready to run an Isaac ROS demo!

### Rank 2

- Score: 0.5118
- Title: isaac_ros_visual_slam
- Source: Isaac ROS docs
- Version: latest
- Section path: isaac_ros_visual_slam > Quickstart > Run Launch File
- URL: https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_visual_slam/isaac_ros_visual_slam/index.html
- Preview: # isaac_ros_visual_slam ## Quickstart ### Run Launch File RosbagRealSense CameraZED Camera Continuing inside the Isaac ROS environment, install the following dependencies: sudo apt-get update sudo apt-get install -y...

### Rank 3

- Score: 0.5095
- Title: isaac_ros_cumotion
- Source: Isaac ROS docs
- Version: latest
- Section path: isaac_ros_cumotion > Robot Segmentation > Quickstart > Run Launch File for Robot Segmentation
- URL: https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_cumotion/isaac_ros_cumotion/index.html
- Preview: # isaac_ros_cumotion ## Robot Segmentation ### Quickstart #### Run Launch File for Robot Segmentation Rosbag Continuing inside the Isaac ROS environment, run the following launch file to spin up a demonstration of...

### Rank 4

- Score: 0.3341
- Title: Tutorial for NITROS Bridge with Isaac Sim
- Source: Isaac ROS docs
- Version: latest
- Section path: Tutorial for NITROS Bridge with Isaac Sim > Tutorial Walkthrough
- URL: https://nvidia-isaac-ros.github.io/concepts/nitros_bridge/tutorial_isaac_sim.html
- Preview: # Tutorial for NITROS Bridge with Isaac Sim ## Tutorial Walkthrough Clone isaac_ros_common repository under a new workspace: mkdir -p ~/isaac_sim_workspaces && \ cd ~/isaac_sim_workspaces && \ git clone -b release-4.3...

### Rank 5

- Score: 0.3139
- Title: Using ros2doctor to identify issues
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Using ros2doctor to identify issues > ros2doctor is part of the ros2cli package. > You can also examine a running ROS 2 system to identify possible causes for issues.
- URL: https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Getting-Started-With-Ros2doctor.html
- Preview: # Using ros2doctor to identify issues ## ros2doctor is part of the ros2cli package. ### You can also examine a running ROS 2 system to identify possible causes for issues. To see ros2doctor working on a running...

## Query 11

- Query: How do I set up the MoveIt getting started tutorial workspace and build it from source?
- Category: procedural
- Retrieval mode: hybrid
- Routed intent: procedural
- Preferred sources: MoveIt docs
- Preferred doc types: getting_started, installation, tutorial

### Rank 1

- Score: 0.6006
- Title: Getting Started
- Source: MoveIt docs
- Version: main
- Section path: Getting Started > Download Source Code of MoveIt and the Tutorials
- URL: https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html
- Preview: # Getting Started ## Download Source Code of MoveIt and the Tutorials Move into your Colcon workspace and pull the MoveIt tutorials source, where <branch> can be e.g. humble for ROS Humble, or main for the latest...

### Rank 2

- Score: 0.4949
- Title: MoveItCpp Tutorial
- Source: MoveIt docs
- Version: main
- Section path: MoveItCpp Tutorial > Getting Started
- URL: https://moveit.picknik.ai/main/doc/examples/moveit_cpp/moveitcpp_tutorial.html
- Preview: # MoveItCpp Tutorial ## Getting Started If you haven’t already done so, make sure you’ve completed the steps in Getting Started.

### Rank 3

- Score: 0.4825
- Title: MoveIt Quickstart in RViz
- Source: MoveIt docs
- Version: main
- Section path: MoveIt Quickstart in RViz > Getting Started
- URL: https://moveit.picknik.ai/main/doc/tutorials/quickstart_in_rviz/quickstart_in_rviz_tutorial.html
- Preview: # MoveIt Quickstart in RViz ## Getting Started If you haven’t already done so, make sure you’ve completed the steps in Getting Started or our Docker Guide. If you followed the Docker Guide, also follow the Create A...

### Rank 4

- Score: 0.4492
- Title: Your First C++ MoveIt Project
- Source: MoveIt docs
- Version: main
- Section path: include <moveit/move_group_interface/move_group_interface.hpp> > 2.1 Build and Run > 3 Plan and Execute using MoveGroupInterface > 3.1 Build and Run
- URL: https://moveit.picknik.ai/main/doc/tutorials/your_first_project/your_first_project.html
- Preview: # Your First C++ MoveIt Project ## 2.1 Build and Run ### 3 Plan and Execute using MoveGroupInterface #### 3.1 Build and Run Just like before, we need to build the code before we can run it. In the workspace directory,...

### Rank 5

- Score: 0.3427
- Title: Creating a workspace
- Source: ROS 2 official docs
- Version: jazzy
- Section path: All required rosdeps installed successfully > In this tutorial, you sourced your main ROS 2 distro install as your underlay, and created an overlay by cloning and building packages in a new workspace.
- URL: https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.html
- Preview: # Creating a workspace ## In this tutorial, you sourced your main ROS 2 distro install as your underlay, and created an overlay by cloning and building packages in a new workspace. The overlay gets prepended to the...

## Query 12

- Query: PX4 build fails with a flash overflow error. What usually causes this and how can I fix it?
- Category: troubleshooting
- Retrieval mode: hybrid
- Routed intent: troubleshooting
- Preferred sources: PX4 official docs
- Preferred doc types: troubleshooting, safety, integration

### Rank 1

- Score: 0.4115
- Title: Building PX4 Software
- Source: PX4 official docs
- Version: v1.16
- Section path: Building PX4 Software > Troubleshooting > Flash overflowed by XXX bytes
- URL: https://docs.px4.io/v1.16/en/dev_setup/building_px4
- Preview: # Building PX4 Software ## Troubleshooting ### Flash overflowed by XXX bytes The region 'flash' overflowed by XXXX bytes error indicates that the firmware is too large for the target hardware platform. This is common...

### Rank 2

- Score: 0.3603
- Title: Installation troubleshooting
- Source: ROS 2 official docs
- Version: jazzy
- Section path: All required rosdeps installed successfully > Sometimes rclpy fails to be imported because of some missing DLLs on your system. > If you run into the CMake error file INSTALL cannot set modification time on ... when installing files it is likely that an anti virus software or Windows Defender are interfering with the build.
- URL: https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html
- Preview: # Installation troubleshooting ## Sometimes rclpy fails to be imported because of some missing DLLs on your system. ### If you run into the CMake error file INSTALL cannot set modification time on ... when installing...

### Rank 3

- Score: 0.2943
- Title: Simulation
- Source: PX4 official docs
- Version: v1.16
- Section path: Simulation
- URL: https://docs.px4.io/v1.16/en/simulation/
- Preview: # Simulation Simulators allow PX4 flight code to control a computer modeled vehicle in a simulated "world". You can interact with this vehicle just as you might with a real vehicle, using QGroundControl, an offboard...

### Rank 4

- Score: 0.2928
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide The ROS 2-PX4 architecture provides a deep integration between ROS 2 and PX4, allowing ROS 2 subscribers or publisher nodes to interface directly with PX4 uORB topics. This topic provides an...

### Rank 5

- Score: 0.1933
- Title: Basic Concepts
- Source: PX4 official docs
- Version: v1.16
- Section path: Basic Concepts > Ground Control Stations > QGroundControl
- URL: https://docs.px4.io/v1.16/en/getting_started/px4_basic_concepts
- Preview: # Basic Concepts ## Ground Control Stations ### QGroundControl The Dronecode GCS software is called QGroundControl ("QGC"). It runs on Windows, Android, MacOS or Linux hardware, and supports a wide range of screen...

## Query 13

- Query: A ROS 2 subscriber is not receiving PX4 topic data correctly. Could QoS incompatibility be the reason, and what should I check?
- Category: troubleshooting
- Retrieval mode: hybrid
- Routed intent: troubleshooting
- Preferred sources: PX4 official docs, ROS 2 official docs
- Preferred doc types: integration, troubleshooting, safety

### Rank 1

- Score: 0.5428
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Compatibility Issues > ROS 2 Subscriber QoS Settings
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Compatibility Issues ### ROS 2 Subscriber QoS Settings ROS 2 code that subscribes to topics published by PX4 must specify a appropriate (compatible) QoS setting in order to listen to topics....

### Rank 2

- Score: 0.4745
- Title: uXRCE-DDS (PX4-ROS 2/DDS Bridge)
- Source: PX4 official docs
- Version: v1.16
- Section path: uXRCE-DDS (PX4-ROS 2/DDS Bridge) > Fast-RTPS to uXRCE-DDS Migration Guidelines > Dependencies do not need to be removed > Default topic naming convention has changed
- URL: https://docs.px4.io/v1.16/en/middleware/uxrce_dds
- Preview: # uXRCE-DDS (PX4-ROS 2/DDS Bridge) ## Fast-RTPS to uXRCE-DDS Migration Guidelines ### Dependencies do not need to be removed #### Default topic naming convention has changed The topic naming format changed: -...

### Rank 3

- Score: 0.3833
- Title: ROS 2 Offboard Control Example
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 Offboard Control Example > Trying it out
- URL: https://docs.px4.io/v1.16/en/ros2/offboard_control
- Preview: # ROS 2 Offboard Control Example ## Trying it out Follow the instructions in ROS 2 User Guide to install PX and run the simulator, install ROS 2, and start the XRCE-DDS Agent. After that we can follow a similar set of...

### Rank 4

- Score: 0.3625
- Title: Installation troubleshooting
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Installation troubleshooting > General troubleshooting techniques apply to all platforms. > rviz2 may fail to start on a Wayland display system with errors like:
- URL: https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html
- Preview: # Installation troubleshooting ## General troubleshooting techniques apply to all platforms. ### rviz2 may fail to start on a Wayland display system with errors like: QSocketNotifier: Can only be used with threads...

### Rank 5

- Score: 0.2047
- Title: Low Level Controllers
- Source: MoveIt docs
- Version: main
- Section path: In your moveit_controllers.yaml configuration > Remapping /joint_states topic
- URL: https://moveit.picknik.ai/main/doc/examples/controller_configuration/controller_configuration_tutorial.html
- Preview: # Low Level Controllers ## Remapping /joint_states topic (TODO: update for ROS2) When you run a move group node, you may need to remap the topic /joint_states to /robot/joint_states, otherwise MoveIt won’t have...

## Query 14

- Query: The ros_gz_bridge clock topic is not publishing for PX4 simulation with ROS 2. What version mismatch or setup issue should I investigate?
- Category: troubleshooting
- Retrieval mode: hybrid
- Routed intent: troubleshooting
- Preferred sources: PX4 official docs, ROS 2 official docs
- Preferred doc types: integration, troubleshooting, safety

### Rank 1

- Score: 0.6028
- Title: ROS 2 User Guide
- Source: PX4 official docs
- Version: v1.16
- Section path: ROS 2 User Guide > Troubleshooting > ros_gz_bridge not publishing on the \clock topic
- URL: https://docs.px4.io/v1.16/en/ros2/user_guide
- Preview: # ROS 2 User Guide ## Troubleshooting ### ros_gz_bridge not publishing on the \clock topic If your ROS2 nodes use the Gazebo clock as time source but the ros_gz_bridge node doesn't publish anything on the /clock...

### Rank 2

- Score: 0.4606
- Title: uXRCE-DDS (PX4-ROS 2/DDS Bridge)
- Source: PX4 official docs
- Version: v1.16
- Section path: uXRCE-DDS (PX4-ROS 2/DDS Bridge) > DDS Topics YAML
- URL: https://docs.px4.io/v1.16/en/middleware/uxrce_dds
- Preview: # uXRCE-DDS (PX4-ROS 2/DDS Bridge) ## DDS Topics YAML subscriptions and subscriptions_multi allow us to choose the uORB topic instance that ROS 2 topics are routed to: either a shared instance that may also be getting...

### Rank 3

- Score: 0.3967
- Title: Simulation
- Source: PX4 official docs
- Version: v1.16
- Section path: Simulation > SITL Simulation Environment
- URL: https://docs.px4.io/v1.16/en/simulation/
- Preview: # Simulation ## SITL Simulation Environment The diagram below shows a typical SITL simulation environment for any of the supported simulators that use MAVLink (i.e. all of them except Gazebo). The different parts of...

### Rank 4

- Score: 0.3952
- Title: Installation troubleshooting
- Source: ROS 2 official docs
- Version: jazzy
- Section path: Installation troubleshooting > General troubleshooting techniques apply to all platforms. > Sometimes rclpy fails to be imported because the expected C extension libraries are not found.
- URL: https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html
- Preview: # Installation troubleshooting ## General troubleshooting techniques apply to all platforms. ### Sometimes rclpy fails to be imported because the expected C extension libraries are not found. If so, compare the...

### Rank 5

- Score: 0.3852
- Title: Gazebo Simulation
- Source: PX4 official docs
- Version: v1.16
- Section path: Gazebo Simulation > Further Information
- URL: https://docs.px4.io/v1.16/en/sim_gazebo_gz/index
- Preview: # Gazebo Simulation ## Further Information - px4-simulation-ignition

## Query 15

- Query: Isaac ROS setup is failing because the system does not meet supported platform requirements. What hardware or software constraints should I verify first?
- Category: troubleshooting
- Retrieval mode: hybrid
- Routed intent: troubleshooting
- Preferred sources: Isaac ROS docs
- Preferred doc types: troubleshooting, safety, integration

### Rank 1

- Score: 0.3604
- Title: Installation troubleshooting
- Source: ROS 2 official docs
- Version: jazzy
- Section path: All required rosdeps installed successfully > Sometimes rclpy fails to be imported because of some missing DLLs on your system. > If running a ROS binary gives the error:
- URL: https://docs.ros.org/en/jazzy/How-To-Guides/Installation-Troubleshooting.html
- Preview: # Installation troubleshooting ## Sometimes rclpy fails to be imported because of some missing DLLs on your system. ### If running a ROS binary gives the error: | failed to create process. It is likely the Python...

### Rank 2

- Score: 0.3464
- Title: Getting Started
- Source: Isaac ROS docs
- Version: latest
- Section path: Getting Started > System Requirements > Supported Platforms
- URL: https://nvidia-isaac-ros.github.io/getting_started/index.html
- Preview: # Getting Started ## System Requirements ### Supported Platforms Platform Hardware Software Storage Notes Jetson Jetson Thor (T5000 and T4000) JetPack 7.1 128+ GB NVMe SSD For best performance, ensure that power...

### Rank 3

- Score: 0.3461
- Title: isaac_ros_visual_slam
- Source: Isaac ROS docs
- Version: latest
- Section path: isaac_ros_visual_slam > Troubleshooting > Troubleshooting Suggestions
- URL: https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_visual_slam/isaac_ros_visual_slam/index.html
- Preview: # isaac_ros_visual_slam ## Troubleshooting ### Troubleshooting Suggestions If the pose estimate frames in RViz is drifting from actual real-world poses and you see white dots on nearby objects(refer to the screenshot...

### Rank 4

- Score: 0.3354
- Title: isaac_ros_cumotion
- Source: Isaac ROS docs
- Version: latest
- Section path: isaac_ros_cumotion > Troubleshooting > Isaac ROS Troubleshooting
- URL: https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_cumotion/isaac_ros_cumotion/index.html
- Preview: # isaac_ros_cumotion ## Troubleshooting ### Isaac ROS Troubleshooting For solutions to problems with Isaac ROS, see troubleshooting.

### Rank 5

- Score: 0.2847
- Title: Isaac for Manipulation Reference Architecture
- Source: Isaac ROS docs
- Version: latest
- Section path: . XRDF (Extended Robot Description Format) file - for collision geometry, definition of > Component 4 - Goal State Estimation > Component 6 - Hardware Platform
- URL: https://nvidia-isaac-ros.github.io/reference_workflows/isaac_for_manipulation/reference_architecture.html
- Preview: # Isaac for Manipulation Reference Architecture ## Component 4 - Goal State Estimation ### Component 6 - Hardware Platform This component consists of hardware platforms and robot arm manipulators on which Isaac for...
