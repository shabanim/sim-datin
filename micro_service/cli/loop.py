from cli import ICommandLineHandler
from analysis.summary import summary
from analysis.utils import read_config, get_config_df, frange, combine_dataframes, update_archbench_config
import argparse
import os
from reports import render_report
from report_objects import format_summary_report, format_loop_summary

def str_to_boolean(s):
    if isinstance(s, bool):
        return s
    if s.lower() in ['true', 't', 'yes', 'y', 'on', 'enable']:
        return True
    elif s.lower() in ['false', 'f', 'no', 'n', 'off', 'disable']:
        return False
    else:
        raise argparse.ArgumentTypeError('expecting boolean value')

class LoopCLIHandler(ICommandLineHandler):
    """
    Loops over given parameter list range(start,end, step) updates config step wise, generates summary report
    """

    @staticmethod
    def get_command():
        return "sweep"

    def __init__(self):
        pass

    def description(self):
        return "Loops over given parameter list range(start,end, step) updates config step wise, generates summary report"

    def _append_str2filename(self, path, ustr):
        filename = os.path.basename(path)
        return path.replace(filename, "{}{}".format(ustr, filename))

    @staticmethod
    def _get_duplicate_config(config):
        if config is None:
            return {}
        return config.copy()

    @staticmethod
    def _get_loop_exec_dict(config, loop_param1, loop_range1, loop_param2=None, loop_range2=None, scaleout_config=None,):
        config_dict = {}
        for i_param in frange(loop_range1):
            loop_config = LoopCLIHandler._get_duplicate_config(config)
            loop_scaleout_config = LoopCLIHandler._get_duplicate_config(scaleout_config)

            if loop_param1 in loop_config.keys():
                loop_config[loop_param1] = i_param
            if loop_param1 in loop_scaleout_config.keys():
                loop_scaleout_config[loop_param1] = i_param
            if loop_param2 is not None:
                config_dict[i_param] = {}
                for j_param in frange(loop_range2):
                    if loop_param2 in loop_config.keys():
                        loop_config[loop_param2] = j_param
                    if loop_param2 in loop_scaleout_config.keys():
                        loop_scaleout_config[loop_param2] = j_param
                    suffix_key = "{}_{}".format(loop_param2, j_param)
                    config_dict[i_param][j_param] = (loop_config, loop_scaleout_config)
            else:
                config_dict[i_param] = (loop_config, loop_scaleout_config)

        return config_dict


    def exec(self, argv):
        args, args_dict = self._parse_command_line_args(argv)

        config_dict = read_config(args.configfile)
        scaleout_dict = read_config(args.scaleout_config)
        if args.sweep_param1 not in config_dict.keys() and args.sweep_param1 not in scaleout_dict.keys():
            raise ("Given loop paramter is not a parameter in config, please provide valid loop parameter")

        loop_exec_dict = LoopCLIHandler._get_loop_exec_dict(config=config_dict, scaleout_config=scaleout_dict,
                                           loop_param1=args.sweep_param1, loop_range1=args.sweep_range1,
                                           loop_param2=args.sweep_param2, loop_range2=args.sweep_range2)

        try:
            out_file_path = config_dict["outFilePath"]
        except:
            out_file_path = "./"
        loop_summary_dfs = {}
        scaling_graph = {}
        thoughput_graph = {}
        archbench_config = args.config_file
        workload_graph = args.input_net_file
        for i_param, value in loop_exec_dict.items():
            if type(value) == dict:
                x = []
                scaling_y = []
                throughput_y = []
                for j_param, (sweep_config, sweep_scaleout) in value.items():
                    update_archbench_config(archbench_config, args.sweep_param1,
                                            i_param, args.sweep_param2, j_param)
                    overlap_summary = summary(args_dict, workload_graph, archbench_config, sweep_config,
                                              self._append_str2filename(args.outputfile,
                                                                        "{}_{}_{}_{}_".format(args.sweep_param1,
                                                                                              i_param, args.sweep_param2,
                                                                                              j_param)),
                                              sweep_scaleout, args.scaleout)
                    config_df = get_config_df(sweep_config, sweep_scaleout, args.scaleout)
                    report = format_summary_report(config_df, overlap_summary)
                    loop_summary_dfs["{} {}, {} {}".format(args.sweep_param1, i_param, args.sweep_param2, j_param)] = overlap_summary.info_df
                    render_report(report, self._append_str2filename("{}SpeedSimAnalysis.html".format(out_file_path),
                                                                    "{}_{}_{}_{}_".format(args.sweep_param1, i_param, args.sweep_param2, j_param)))
                    x.append(j_param)
                    scaling_y.append(overlap_summary.info_df['Value'][5])
                    throughput_y.append(overlap_summary.info_df['Value'][9])

                scaling_graph["{} {}".format(args.sweep_param1, i_param)] = (x, scaling_y)
                thoughput_graph["{} {}".format(args.sweep_param1, i_param)] = (x, throughput_y)
            else:
                (sweep_config, sweep_scaleout) = value
                update_archbench_config(archbench_config, args.sweep_param1,
                                        i_param)
                overlap_summary = summary(args_dict, workload_graph, archbench_config, sweep_config,
                                          self._append_str2filename(args.outputfile,
                                                                    "{}_{}_".format(args.sweep_param1, i_param)),
                                          sweep_scaleout, args.scaleout, args.ss_detailed_report)
                config_df = get_config_df(sweep_config, sweep_scaleout, args.scaleout)
                report = format_summary_report(config_df, overlap_summary, args.ss_detailed_report)
                loop_summary_dfs["{} {}".format(args.sweep_param1, i_param)] = overlap_summary.info_df
                render_report(report, self._append_str2filename("{}SpeedSimAnalysis.html".format(out_file_path),
                                                                "{}_{}_".format(args.sweep_param1, i_param)))
                scaling_graph[i_param] = overlap_summary.info_df['Value'][5]
                thoughput_graph[i_param] = overlap_summary.info_df['Value'][9]
        loop_summary_df = combine_dataframes(
            dataframes=loop_summary_dfs, index=["Metric"]
        )

        loop_report = format_loop_summary(loop_summary_df, sweep_param1=args.sweep_param1, sweep_param2=args.sweep_param2,
                                          scaling_graph=scaling_graph, thoughput_graph=thoughput_graph)
        render_report(loop_report, "{}Loop_summary.html".format(out_file_path))
        print("Loop executed")


    @staticmethod
    def _parse_command_line_args(argv):
        parser = argparse.ArgumentParser(prog="./micro_service/dl-modelling.py {}".format(LoopCLIHandler.get_command()),
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('-sp1', '--sweep_param1', type=str, required=True)
        parser.add_argument('-sr1', '--sweep_range1', type=str, required=True)

        parser.add_argument('-sp2', '--sweep_param2', type=str, default=None)
        parser.add_argument('-sr2', '--sweep_range2', type=str, default=None)

        parser.add_argument('-c', '--configfile', type=str, required=True)
        parser.add_argument('-o', '--outputfile', type=str, default="Report.csv")
        parser.add_argument('-so', '--scaleout', action="store_true", default=False)
        parser.add_argument('-so_config', '--scaleout_config', type=str)
        parser.add_argument('-cf', '--config_file', help='Specify the configuration .yaml to use)')
        parser.add_argument('-ssd', '--ss_detailed_report', action='store_true',
                            help='include speedsim detailed results')

        parser.add_argument('--no_backup',
                            action='store_true',
                            help='Create missing results directories, but do not move the old ones')
        parser.add_argument('-wl', '--workload_config_file', help='Specify the workload configuration .yaml to use)')
        parser.add_argument('-f',
                            '--input_net_file',
                            default="networks/default.lst",
                            help='Input network prototxt, onnx, yaml or list (.lst) file else the \
                                                  default.lst caffe networks are used')
        parser.add_argument('-r', '--runs', type=int, help='Input number of times the network list is run')
        parser.add_argument('-rf', '--refeed', action='store_true', help='Refeed network output as input')
        parser.add_argument('-sf',
                            '--sparsity_file',
                            help='Sparsity data, works only in Input-Single mode, default is to \
                                                  take file that matches network name')
        parser.add_argument('-cmpf',
                            '--compression_file',
                            help='Compression data, works only in Input-Single mode, default is to \
                                                  take file that matches network name')
        parser.add_argument('-tfirst',
                            '--timefirst',
                            action='store_true',
                            help='Run networks through timeFirst instead of depthFirst')
        parser.add_argument('-v', '--verbose', action='store_true', help='Enable Verbose mode')
        parser.add_argument('-j',
                            '--threads',
                            type=int,
                            default=1,
                            choices=range(1, 9),
                            help='Number of threads to run in parallel (linux only)')
        parser.add_argument('-oc',
                            '--override_cfg',
                            action='append',
                            help='Override configurations from command line \
                                                  1.Usage - Input yaml  overrides in dictionary format. \
                                                      Example -oc "Device: {enable_fusion: 1}" \
                                                  2.Usage - Multiple yaml overrides in single commandline. \
                                                      Example -oc "Device: {enable_fusion: 1, enable_pipeline: 1}" -oc "MPEngine: {nEngines: 256}" \
                                                      -oc "SHAVEngine: {nEngines: 256}" \
                                                  3. Usage - lists, list of lists format. \
                                                      Example -oc "Device: {deviceFreq:[700,800,900], cacheSizes: [[3],[4],[5,6]]}"')
        parser.add_argument('-id',
                            '--input_dims',
                            nargs='+',
                            help='The input tensor size; delimiter between dimensions should be \
                                                  \'x\' of the form: channelxheightxwidth or any smaller subset \
                                                  of parameters from the right. For multiple input dimensions \
                                                  separate with space. Example: \'-id 3x223x223 3x223x223\'')
        parser.add_argument('-os',
                            '--output_stats',
                            action='store_true',
                            help='Print the last iteration of the run\'s final FPS value and OPS value')

        parser.add_argument('--logging',
                            default=[],
                            nargs=2,
                            action='append',
                            help='set logging level for arg-1 to arg-2; e.g. --log dlest.simulator DEBUG2')

        parser.add_argument('--dump_html',
                            action='store_true',
                            help='Saves an HTML and JSON file in the results directory for visualization.')

        parser.add_argument('--no_reports', action='store_true', help='Disables report generation.')
        trainingparser = parser.add_argument_group('training')
        trainingparser.add_argument('--training', action='store_true', help='Do a training run')
        trainingparser.add_argument(
            '--trg-corr',
            action='store_true',
            dest='training_correlation',
            help='Activate knobs for training correlation; use only for co-relation and not for reporting')
        trainingparser.add_argument('--trg-optimizer',
                                    dest='trg_optimizer',
                                    choices=['adam', 'sgd'],
                                    help='optimizer for training')
        trainingparser.add_argument('--trg-loss-function',
                                    dest='trg_loss_function',
                                    choices=['crossentropy', 'meansquarederror'],
                                    help='loss function for training')
        trainingparser.add_argument(
            '--trg-per-layer-flush',
            '--trg-greedy-flush',
            dest='trg_per_layer_flush',
            type=str_to_boolean,
            help='flush cache forcibly after every forward layer; use only for co-relation, not for reporting')
        trainingparser.add_argument('--trg-endofpass-flush',
                                    dest='trg_endofpass_flush',
                                    type=str_to_boolean,
                                    help='enable end of pass flush')

        trainingparser.add_argument('--trg-imm-wt-update',
                                    dest='trg_imm_wt_update',
                                    type=str_to_boolean,
                                    help='Do immediate weight update after calculating weight gradient.\n' +
                                         'DO NOT defer weight update and optimizer step until end of all of backward pass.')
        trainingparser.add_argument(
            '--trg-bwd-pipe-layer-inp-save',
            dest='trg_pipe_layer_inp_save',
            type=str_to_boolean,
            help='Save inputs of intermediate pipelined layers, if needed for their bwd.\n' +
                 'Read these inputs for pipelined layers during bwd pass. **CURRENTLY assuming no overcompute.***')
        trainingparser.add_argument(
            '--trg-resnet-specific',
            dest='trg_resnet_specific',
            action='store_true',
            help='Enable resnet specific decisions - (1) read output actions as well on backward pass for' +
                 'conv layers part of a pipelined block')

        args = parser.parse_args(argv)

        args_dict = {}
        args_dict.update(vars(args))
        args_dict.pop("configfile")
        args_dict.pop("outputfile")
        args_dict.pop("scaleout")
        args_dict.pop("scaleout_config")
        args_dict.pop("sweep_param1")
        args_dict.pop("sweep_range1")
        args_dict.pop("sweep_param2")
        args_dict.pop("sweep_range2")
        args_dict.pop("ss_detailed_report")

        return (args, args_dict)
