# LODUS
 
Instructions!

Type this in powershell:
    batch_experiments.ps1 [data_input_file] > experiments.ps1
    experiments.ps1


Runs 4 experiments combining:
    [day infection; fixed rate infection] and [fixed rate mobility; inloco matrix]

If you desire to run a single experiment:
    python ./simulator.py --i 1 --s 1 --f [data_input_file]
    --i and --s define the infection and mobility plugin parameters to use.
    This is an example placeholder.


Data Input file:
    Grammar is described in DataInputDescription.txt
    It's a bit outdated. The DataInput folder has several working files to serve as examples.
    (for example, Test_Patient0_AllRegions.json)

Simulator :
    The file simulator.py has most of the initialization and general parameters of the simulator.
    It should be (somewhat) self-explanatory.


Logging:
    The logging is handled by the SimulationLogger class.
    This current logger records mostly infection data.
    You need to add which types of files you want recorded.
    'global'
        The total susceptible, infected, removed population per frame.
    'neighbourhood'
        Per region total susceptible, infected, removed population per frame.
    'graph'
        The raw output of the simulator per frame.
        WARNING. HUGE HUGE HUGE OUTPUT.


Plugins:
    The simulator by default contains only the "move_population" action.
    The "move_population" moves a quantity of population from one node to another.
    This can describe most of human mobility, going from point A to point B, but isn't descriptive enough.
    Plugins can also directly invoke a Blob.move_pop() method.
        Blob.move_pop() moves crowds between PropertyBlocks, this simulates profile tracked features.
            Infection, lottery winners, and so on.


    Plugins add extra actions to the simulator.
    These extra actions are usually broken up into several "move_population" actions.


    Plugin 'install' template (kinda usually works like this.):

        graph = EnvironmentGraph()
        plugin = SomePlugin(graph, additional_construction_parameters)
        plugin.additional_initialization_whatever(yada, yada)

        graph.LoadPlugin(plugin)


"move_population"
    The default movement action.

    has parameters:
        origin_region: origin region.
        origin_node: origin node.
        destination_region: destination region.
        destination_node: destination node.
        quantity: population size to be moved.
        population_template: PopTemplate to be matched by the operation.





Mobility Plugins:

    The GatherPopulationPlugin and  SocialIsolationPlugin inject the operation "gather_population" into the simulation.

    "gather_population" has parameters:
        "region"
            name of destination region. (yes. it is kinda redundant.)
        "node"
            name of destination node. (yes. it is kinda redundant.)
        "quantity"
            The quantity to be gathered.
        "population_template"
            population template
    
    
    The GatherPopulationPlugin has the following constructor parameter:
        isolation_rate
            How much to reduce the gather_population quantities by. Value in range [0,1]. 
            An isolation rate of 0.2 causes 80% of the regular crowds to move.
            0.3 causes 70% and so on.


    The SocialIsolationPlugin has the following constructor parameter:

        isolation_table_path
            The path to a csv table containing the described social isolation data.


    SocialIsolationPlugin and GatherPopulationPlugin are mutually exclusive.


Infection Parameters:

    The infection plugin injects the operation "infect" into the simulation.

    "infect" has paramenters:
        "beta": 0.25,
            SIR model beta: rate in which Susceptible become Infected
        "gamma": 0.08,
            SIR model gamma: rate in which Infected become Removed
        "sigma": 0.03,
            SEIR model sigma: rate in which Infected become Removed. In this case, beta is the ratein which Susceptible become Exposed, and gamma is the rate Exposed become Infected.
        "mu": 0.0,
            Accounts to natural death rate of the population, not related to the epidemics.
        "nu": 0.0,
            Accounts to vaccination rate, and moves individuals from Susceptible to Removed directly.
        "population_template"
            The population template


    The InfectionPlugin object has the following constructor parameters:

    infect_mode
        defines which infect mode to use. 0 for fixed rate. 1 for day based.
        for the fixed rate infection, 

    use_infect_move_pop
        defines if move population attempts to infect blobs as they move (kinda simulates public transport).

    default_beta
        default SIR model beta. used for fixed rate travel infection

    default_gamma
        default SIR model gamma. used for fixed rate travel infection



    Additionally:

        The user can the following properties:
            bus_density
                density for move population infection

            home_density
                density for the recurring infection


        In case of fixed rate infection, the gamma and beta of recurring infection are set in the data input file.



TODO FEATURE LIST

Load an output graph description as simulation input.
    Plug and play simulations, can pause, change settings and continue 2 different simulations, etc.


A more scientific GatherPopulation plugin.
    Preferably a faster more efficient operation.
    Maybe neighbour based.


Fix all the TODOs