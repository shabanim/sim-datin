# SpeedSim

**SPEEDSIM** is an abstract system simulation package for architectural exploration.

It consists of two main modules:
* **asap** (**a**bstract **s**imulation **a**rchitecture **p**ackage): provides interfaces for defining SOC component structure and abstract workloads.
* **pnets** (**p**etri **nets**): task graph modeling and dynamic simulation.

Using these packages one can:
* **Build an abstract platform model** by defining processing blocks and connectivity between the blocks (CPUs, GPUs, memories, ..)
* **Define abstract workload** (inter-dependent tasks associated with processing and memory attributes)
* **Perform dynamic simulation** of the workload using specified platform for power/performance projections

Additionally SPEEDSIM provides ways to extend the simulation with:
 * **Power state modeling** for component power states and frequency manipulation
 * **Fabric modeling** for bandwidth-aware performance simulation
 * **Task scheduling algorithms** for exploring effects of task scheduling on system performance
 * ...
 
It provides both **command-line tool** as well as **python API**.

#### _Setup instructions:_
Start by cloning the project, if already clone, make sure to be up-to-date.
* git clone --recurse-submodules ssh://git@gitlab.devtools.intel.com:29418/speed-public-pkgs/speedsim.git
* Command line: TBD
* Jupyter notebooks:
    * From python area open jupyter: 
    
            jupyter-lab --ip='0.0.0.0' <notebooks dire>
            
         where notebooks dir is working area to work and save notebooks.
         _Note: make sure jupyter-lab is installed in python_
         Running the above command will print a link starts with machine identifier.
         Copy and paste link in Chrome after removing redundant fields from it.
         
            Command print similar to:
            http://(icsl3011 or 127.0.0.1):8890/?token=<id>
            Copy only:
            http://icsl3011:8890/?token=<id>
            
     * Example of notebooks are located in <git>/speedsim/notebooks. Could be a good starting point.
     * To start private notebook:
     
        * Open new notebook from opened jupyter
        * Start first cell by adding project path to imported packages
        
                import sys
                path = '<git_path>/speedsim/'
                if path not in sys.path:
                    sys.path.append(path)
                    
    * Enjoy!

# Detailed Documentation
[Link to detailed API documentation](https://speed-public-pkgs.gitlab-pages.devtools.intel.com/speedsim)
    
### _Best regards_
### _SpeedSim development group_


