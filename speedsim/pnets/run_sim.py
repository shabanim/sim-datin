"""
Top-level script to run simulation from command line
"""
import argparse
import json
import os
import sys
import tempfile

import pandas


def _display_results(results, output):
    """
    Render results using Bokeh
    """
    import bokeh.plotting
    import bokeh.io
    import bokeh.resources
    from pnets.plotting import interval_graph
    import webbrowser

    # WA: specify dummy categorical y_range so that figure Y axis is setup for categorical data
    fig = bokeh.plotting.figure(plot_width=1000, plot_height=600, tools="xpan,xwheel_zoom,reset", y_range=['a', 'b'])
    interval_graph(fig, results)

    bokeh.io.save(fig, output, resources=bokeh.resources.CDN, title="SPEEDSIM Simulation Results")
    webbrowser.open(output)


def _simulate(args):
    """
    'simulate' sub-command handler
    """
    from pnets import PnmlModel
    from pnets.simulation import simulate_model

    # read PNML file
    with open(args.file) as stream:
        pnml = PnmlModel.read(stream)

    if args.resources.endswith('.json'):
        with open(args.resources) as stream:
            resources = json.load(stream)
    else:
        resources = {}
        for s in args.resources.split(','):
            resource, count = map(str.strip, s.split('='))
            count = int(count)
            resources[resource] = count

    results = simulate_model(pnml, resources, args.duration)

    # save results
    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    results.to_csv(os.path.join(args.output_dir, "results.csv"), index=False)

    if args.display:
        dest_html = os.path.join(args.output_dir, 'results.html')
        _display_results(results, dest_html)


def _display(args):
    """
    Display sub-command handler
    """
    results = pandas.read_csv(args.file)
    fd, tmp_name = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    _display_results(results, tmp_name)


def _stats(args):
    """
    Dispay task graph statistics
    """
    # from pnets import PnmlModel
    #
    # with open(args.file) as stream:
    #     model = PnmlModel.read(stream)

    pass


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', title="Sub-commands", help="Supported sub-commands")

    # simulate sub-command
    sim_parser = subparsers.add_parser("simulate")
    sim_parser.add_argument("-f", "--file", help="Extended .pnml file to simulate", type=str, required=True)
    sim_parser.add_argument("-r", "--resources",  type=str, required=True,
                            help="HW resource specification. "
                                 "Either a path to a .json file or HW=<count>,HW2=<count2>,...")
    sim_parser.add_argument("-d", "--duration", help="Time duration to simulate (usec)", type=float, default=1000000)
    sim_parser.add_argument("-o", "--output-dir", help="Output directory for the simulation results.", required=True)
    sim_parser.add_argument("-i", "--display", help="Display results using browser", required=False,
                            action='store_true')
    # sim_parser.set_defaults(_simulate)

    # display sub-command
    disp_parser = subparsers.add_parser("display")
    disp_parser.add_argument("-f", "--file", help="Simulation results file to display", type=str, required=True)
    # disp_parser.set_defaults(_display)

    # stats sub-command
    stats_parser = subparsers.add_parser("stats")
    stats_parser.add_argument("-f", "--file", help="PNML file to load", type=str, required=True)

    args = parser.parse_args()

    # make sure "pnets" are in PYTHONPATH
    script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

    if args.command == 'simulate':
        _simulate(args)
    elif args.command == 'display':
        _display(args)
    elif args.command == 'stats':
        _stats(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
