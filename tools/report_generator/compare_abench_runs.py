import json
import argparse
import sys
import os
import pandas as pd
import itertools


class ReportGenerator():
    def __init__(self,
                 template_dir='tools/report_generator/',
                 output_dir='deleteme',
                 epsilon=0.001,
                 report_differences_only=False):
        self.template_dir = template_dir
        self.outdir = output_dir
        self.epsilon = epsilon
        self.generated_reports = []
        self.dir_exact_match = False
        self.report_differences_only = report_differences_only
        self.create_inference_summary()

    def generate_all_reports(self, dir1, dir2):
        '''
        Generate All Reports is usually the base results directories. It wants
        to find all the common configuration results folders and compare the
        contents of those folders.

        Input Parameters
        ----------------
        dir1: The left directory in the diff.
        For example golden_results/results-test-usecase

        dir2: The right directory in the diff.
        For example results/

        Returns
        -------
        Returns if True if there was an differences in the directories and files
        below this point.
        '''
        dir1list = os.listdir(dir1)
        dir2list = os.listdir(dir2)

        common = list(set(dir1list).intersection(dir2list))
        uncommon = list(set(dir1list).difference(dir2list))

        results = []

        # At this level we may see configuration folders that are not
        # generated I think it is best if we do not count this as a
        # difference. Flag will dictate the behavior here.
        if uncommon:
            if self.dir_exact_match:
                results.append(True)
            print('Some files in dir1({}) and dir2({}) are not shared:'.format(dir1, dir2))
            print('-' * 20)
            for filename in uncommon:
                print(filename)
            print('-' * 20)

        # At this level we need to find at least one common configuration
        # otherwise I'm not sure why you would have bothered running the tool.
        if not common:
            results.append(True)
            print('dir1({}) and dir2({}) do not share any common files'.format(dir1, dir2))

        # Check all the configurations common between the two directories.
        for filename in common:
            file1path = '{}/{}'.format(dir1, filename)
            file2path = '{}/{}'.format(dir2, filename)

            if os.path.isdir(file1path):
                results.append(self.generate_config_reports(file1path, file2path))
            else:
                # You should not find any files at this level. But just in case
                # we can attempt to check the files.
                results.append(self.generate_file_report(file1path, file2path, config='', network=''))

        return any(results)

    def generate_config_reports(self, dir1, dir2, config=None):
        '''
        Generate Configuration Reports is usually the base configuration results
        directories. It wants to find all the common networks results folders
        and compare the contents of those folders.

        Input Parameters
        ----------------
        dir1: The left directory in the diff.
        For example golden_results/results-test-usecase/results-<configuration>/

        dir2: The right directory in the diff.
        For example results/results-<configuration>/

        Returns
        -------
        Returns if True if there was an differences in the directories and files
        below this point.
        '''
        dir1list = os.listdir(dir1)
        dir2list = os.listdir(dir2)

        common = list(set(dir1list).intersection(dir2list))
        uncommon = list(set(dir1list).difference(dir2list))

        results = []

        path = dir1
        path, dir_config = os.path.split(path)

        if config is None:
            config = dir_config.replace('results-', '')

        # At this level we may see network folders that are not
        # generated I think it is best if we do not count this as a
        # difference. Flag will dictate how to behave here.
        if uncommon:
            if self.dir_exact_match:
                results.append(True)
            print('Some files in dir1({}) and dir2({}) are not shared:'.format(dir1, dir2))
            print('-' * 20)
            for filename in uncommon:
                dir_path = dir1 if filename in dir1list else dir2
                print('{}/{}'.format(dir_path, filename))
            print('-' * 20)

        if not common:
            results.append(True)
            print('dir1({}) and dir2({}) do not share any common files'.format(dir1, dir2))

        for filename in common:
            file1path = '{}/{}'.format(dir1, filename)
            file2path = '{}/{}'.format(dir2, filename)
            if os.path.isdir(file1path):
                results.append(self.generate_network_reports(file1path, file2path, config=config))
            else:
                results.append(self.generate_file_report(file1path, file2path, config=config, network=''))

        return any(results)

    def generate_network_reports(self, dir1, dir2, config=None, network=None):
        '''
        Generate Network Reports is usually the network results directories.
        It wants to find all the common networks results folders and compare
        the contents of those folders.

        Input Parameters
        ----------------
        dir1: The left directory in the diff.
        For example golden_results/results-test-usecase/results-<configuration>/<network>

        dir2: The right directory in the diff.
        For example results/results-<configuration>/<network>

        Returns
        -------
        Returns if True if there was an differences in the directories and files
        below this point.
        '''
        dir1list = os.listdir(dir1)
        dir2list = os.listdir(dir2)

        common = list(set(dir1list).intersection(dir2list))
        uncommon = list(set(dir1list).difference(dir2list))

        results = []

        # Chunking up the directory path. This will be useful if we need to
        # recover any information found in the file path.
        path = dir1
        path, dir_network = os.path.split(path)
        path, dir_config = os.path.split(path)

        # Recover the network from the file path if the network was not
        # provided already.
        if network is None:
            network = dir_network

        # Recover the configuration from the file path if config was not
        # provided already.
        if config is None:
            config = dir_config.replace('results-', '')

        # At the network folder level, there should be no differences in the
        # directory structure. At this point everything in dir1 must be in dir2
        if uncommon:
            results.append(True)
            print('Some files in dir1({}) and dir2({}) are not shared:'.format(dir1, dir2))
            print('-' * 20)
            for filename in uncommon:
                dir_path = dir1 if filename in dir1list else dir2
                print('{}/{}'.format(dir_path, filename))
            print('-' * 20)

        # If there are no common files for checking, then there may be an issue
        # with whatever was generated.
        if not common:
            results.append(True)
            print('dir1({}) and dir2({}) do not share any common files'.format(dir1, dir2))

        # Got through the list of common files and generate a report where applicable.
        for filename in common:
            csv1 = '{}/{}'.format(dir1, filename)
            csv2 = '{}/{}'.format(dir2, filename)

            results.append(self.generate_file_report(csv1, csv2, config=config, network=network))

        return any(results)

    def generate_file_report(self, csv1, csv2, html=None, report_name=None, config=None, network=None):
        '''
        Generate file report will attempt to take the two input files and figure
        out what type of report needs to be generated. It will execute the
        corresponding report generator. This function presently only handles
        CSV files. If anything else is provided it will be skipped.

        Input Parameters
        ----------------
        csv1: left csv file from a diff.

        csv2: right csv file from a diff.

        report_name: [optional] Helps designate the appropriate report type. If
        not provided it will be derrived from the input filename.

        html: [optional] The target report HTML file. If it is not provided then
        a file name will be generated based on the config, network and report
        name.

        config: [optional] The configuration that was used to generate the
        original file. This can be derrived from the filepath.

        network: [optional] The network that was used to generate the original
        file. This can be derrived from the filepath.

        Returns
        -------
        Returns if there were any differences in the directory or the files
        within.
        '''
        if report_name is None or config is None or network is None:
            path, local_csv_file = os.path.split(csv1)
            path, local_net_name = os.path.split(path)
            path, local_cfg_name = os.path.split(path)

        if network is None:
            network = local_net_name

        if report_name is None:
            report_name = local_csv_file.replace('.csv', '').rstrip()

            if network != '':
                report_name = report_name.replace(network + '_', '')

        if config is None:
            config = local_cfg_name.replace('results-', '')

        if html is None:
            html = '{}/{}_{}_{}.html'.format(self.outdir, config, network, report_name)

        html = html.replace('__', '_')

        if report_name.startswith('cache_residency'):
            differences = self.generate_residency_report(csv1, csv2, html, config=config, network=network)
        elif report_name.startswith('layer_stat'):
            differences = self.generate_layer_stats_report(csv1, csv2, html, config=config, network=network)
        elif report_name.startswith('stats'):
            differences = self.generate_layer_run_report(csv1, csv2, html, config=config, network=network)
        elif report_name.startswith('summary_stats'):
            differences = self.generate_network_report(csv1, csv2, html, config=config, network=network)
        elif report_name.endswith('Inference'):
            differences = self.generate_inference_report(csv1, csv2, html, config=config, network=network)
        elif csv1.endswith('.csv'):
            differences = self.generate_generic_report(csv1, csv2, html, config=config, network=network)
        else:
            print('Generate File Report unhandled report type {}'.format(report_name))
            differences = False

        return differences

    def generate_report(self,
                        csv1,
                        csv2,
                        html,
                        unique_cols,
                        numeric_cols,
                        non_numeric_cols,
                        report_type='Unknown',
                        report_name='Unknown',
                        config='Unknown',
                        network='Unknown',
                        store_inference=False,
                        remove_row_indicies=None):
        '''
        Returns
        -------
        If there is a difference betweent he two CSV files this function
        returns True.
        '''
        merged, differences = self.compare_statfiles(csv1,
                                                     csv2,
                                                     unique_cols,
                                                     numeric_cols,
                                                     non_numeric_cols,
                                                     remove_row_indicies=remove_row_indicies)
        if merged is not None:
            result = self.generate_html_report(csv1, csv2, html, merged, unique_cols, numeric_cols, non_numeric_cols)

            # Differentes in the current file, plus any details found in the generate_html_report.
            differences = differences or not result

            if store_inference:
                self.append_inference(merged, config=config, html=html, report_name=report_name)

            merged = None

            # Create an entry in the generated reports table. This will be used
            # later in the reports summary html generation.
            self.generated_reports.append({
                'type': report_type,
                'report': report_name,
                'config': config,
                'network': network,
                'csv1': csv1,
                'csv2': csv2,
                'html': html,
                'result': result
            })

            if differences:
                print('Differences found, check report {}'.format(html))
            else:
                print('Passed checks, report generated report {}'.format(html))
        else:
            print('Skipped checks, reports were identical for {}'.format(html))

        return differences

    def create_inference_summary(self):
        self.inference_unique_cols = [
            'Configuration', 'Report', 'Use Case', 'Cache Storage Option', 'Cache Size (Mi)', 'Batch', 'Link'
        ]
        self.inference_numeric_cols = [
            'FPS', 'Freq (M)', 'act_sparsity', 'param_sparsity', 'numUnits', 'wtCompression', 'actCompression',
            'wPrec (Bpe)', 'dPrec (Bpe)', 'BW Threshold (G)', 'IP RD BW (G)', 'IP WR BW (G)', 'Compute OPS (G)',
            'Total MEM RD/WR BW per Sec (G)', 'Total MEM RD BW per Sec (G)', 'Total MEM WR BW per Sec (G)',
            'Activation MEM RD/WR BW per Sec (G)', 'Activation MEM RD BW per Sec (G)',
            'Activation MEM WR BW per Sec (G)', 'Param MEM RD BW per Sec (G)', 'Total CACHE RD/WR BW per Sec (G)',
            'Total CACHE RD BW per Sec (G)', 'Total CACHE WR BW per Sec (G)', 'Total Use (Mi)', 'Data Use (Mi)',
            'Parameter Use (Mi)', 'Perf Cycles', 'Comp Cycles', 'Engine Cycles', 'Data Cycles', 'Cache Cycles',
            'Activation Cycles', 'Parameter Cycles', 'CMP Bound', 'MEM Bound', 'CACHE Bound', 'ENG Bound'
        ]
        self.inference_non_numeric_cols = ['Input Dimensions']

        self.inference_summary = pd.DataFrame(columns=self.inference_unique_cols)
        self.inference_summary.set_index(self.inference_unique_cols, inplace=True, drop=True)

    def append_inference(self, merged, config, html, report_name):
        merged['Configuration'] = config
        merged['Report'] = report_name
        merged['Link'] = '<a href="{}">Link</a>'.format(html.replace(self.outdir, '.'))
        merged.set_index(self.inference_unique_cols, inplace=True, drop=True)
        inference_cols = [
            c + e for c in self.inference_numeric_cols + self.inference_non_numeric_cols
            for e in [' (csv1)', ' (csv2)', ' Difference', ' Percentage Difference (%)', ' Passed']
        ]

        passed_cols = [c + ' Passed' for c in self.inference_numeric_cols + self.inference_non_numeric_cols]
        merged['Passed'] = (merged[passed_cols] == True).all(axis=1)

        columns = ['Passed']
        columns.extend(inference_cols)

        if len(self.inference_summary) > 0:
            self.inference_summary = self.inference_summary.append(merged[columns])
        else:
            self.inference_summary[columns] = merged[columns]

    def generate_inference_report(self, csv1, csv2, html, config='Unknown', network='Unknown'):
        unique_cols = ['Use Case', 'Cache Storage Option', 'Cache Size (Mi)', 'Batch']
        # Ignoring some engine specific columns
        numeric_cols = [
            'FPS', 'Freq (M)', 'numUnits', 'wtCompression', 'actCompression', 'param_sparsity', 'act_sparsity',
            'wPrec (Bpe)', 'dPrec (Bpe)', 'BW Threshold (G)', 'IP RD BW (G)', 'IP WR BW (G)', 'Compute OPS (G)',
            'Total MEM RD/WR BW per Sec (G)', 'Total MEM RD BW per Sec (G)', 'Total MEM WR BW per Sec (G)',
            'Activation MEM RD/WR BW per Sec (G)', 'Activation MEM RD BW per Sec (G)',
            'Activation MEM WR BW per Sec (G)', 'Param MEM RD BW per Sec (G)', 'Total CACHE RD/WR BW per Sec (G)',
            'Total CACHE RD BW per Sec (G)', 'Total CACHE WR BW per Sec (G)', 'Total Use (Mi)', 'Data Use (Mi)',
            'Parameter Use (Mi)', 'Perf Cycles', 'Comp Cycles', 'Engine Cycles', 'Data Cycles', 'Cache Cycles',
            'Activation Cycles', 'Parameter Cycles', 'CMP Bound', 'MEM Bound', 'CACHE Bound', 'ENG Bound'
        ]
        non_numeric_cols = ['Input Dimensions']

        if 'Static' in html:
            report_name = 'Static Inference'
            numeric_cols.extend(['Batches Per Second', 'Device Bound Layer Count', 'Mac Eff'])
        else:
            report_name = 'Dynamic Inference'

        # Adding back in engine specific columns
        self.get_report_headers(csv1, unique_cols, numeric_cols, non_numeric_cols)
        self.get_report_headers(csv2, unique_cols, numeric_cols, non_numeric_cols)

        return self.generate_report(csv1,
                                    csv2,
                                    html,
                                    unique_cols,
                                    numeric_cols,
                                    non_numeric_cols,
                                    report_type='Configuration',
                                    report_name=report_name,
                                    config=config,
                                    network=network,
                                    store_inference=True)

    def generate_network_report(self, csv1, csv2, html, config='Unknown', network='Unkown'):
        unique_cols = ['Network', 'Storage Option', 'Cache Size (Mi)']
        # Some columns are device specific: 'MPE Bound (%)', 'PPE Bound (%)', 'SHAVE Bound (%)', 'MPE Util', 'PPE Util', 'SHAVE Util'
        numeric_cols = [
            'FPS', 'Ideal FPS', 'Number of Layers', 'Total Num Ops (M)', 'Total Input Data Size (Ki)',
            'Total Output Data Size (Ki)', 'Total Parameter Data Size (Ki)', 'Total Read Data Transfer (Ki)',
            'Total Write Data Transfer (Ki)', 'Total Read Parameter Data Transfer (Ki)', 'Total Data Transfer (Ki)',
            'CMX Write Data Transfer (Ki)', 'Perf Cycles', 'Comp Cycles', 'Engine Cycles', 'Cache Cycles',
            'Activation Cycles', 'Parameter Cycles', 'Effective Cycles', 'Ideal Cycles', 'Compute Efficiency (%)',
            'Batches Per Second', 'Ideal Batches Per Second', 'ETOPS(%)', 'Device Bound Layer Count', 'CMP Bound',
            'MEM Bound', 'CACHE Bound', 'ENG Bound'
        ]
        non_numeric_cols = []

        # adding back in engine specific columns
        self.get_report_headers(csv1, unique_cols, numeric_cols, non_numeric_cols)
        self.get_report_headers(csv2, unique_cols, numeric_cols, non_numeric_cols)

        return self.generate_report(csv1,
                                    csv2,
                                    html,
                                    unique_cols,
                                    numeric_cols,
                                    non_numeric_cols,
                                    report_type='Network',
                                    report_name='Network',
                                    config=config,
                                    network=network)

    def generate_layer_run_report(self, csv1, csv2, html, config='Unknown', network='Unkown'):
        unique_cols = ['Layer Index', 'Layer Name']
        numeric_cols = [
            'Cache Size (Mi)', 'Read Param Transfer (Ki)', 'Read Data Transfer (Ki)', 'Write Data Transfer (Ki)',
            'Total Data Transfer (Ki)', 'CMX Write Data Transfer (Ki)', 'Ideal Cycles', 'Effective Cycles',
            'Perf Cycles', 'Comp Cycles', 'Engine Cycles', 'Data Cycles', 'Cache Cycles', 'Activation Cycles',
            'Parameter Cycles', 'Total MEM RD/WR BW per Sec (G)', 'Activation MEM RD/WR BW per Sec (G)',
            'Activation MEM RD BW per Sec (G)', 'Activation MEM WR BW per Sec (G)', 'Param MEM RD BW per Sec (G)',
            'Total CACHE RD/WR Bytes Transferred', 'Total CACHE RD Bytes Transferred',
            'Total CACHE WR Bytes Transferred', 'HW Efficiency (%)', 'HW Utilization (%)', 'Tiling Efficiency (%)',
            'Mem occupied (Ki)'
        ]
        non_numeric_cols = ['Fused', 'Storage Option', 'Layer Bound', 'Tile', 'Bound by device']

        # adding back in engine specific columns
        self.get_report_headers(csv1, unique_cols, numeric_cols, non_numeric_cols)
        self.get_report_headers(csv2, unique_cols, numeric_cols, non_numeric_cols)

        return self.generate_report(csv1,
                                    csv2,
                                    html,
                                    unique_cols,
                                    numeric_cols,
                                    non_numeric_cols,
                                    report_type='Network',
                                    report_name='Layer Stats',
                                    config=config,
                                    network=network)

    def generate_residency_report(self, csv1, csv2, html, config='Unknown', network='Unkown'):

        unique_cols = ['Layer Number', 'Name']
        # Majority of the report is non-predeterministic headers. Need to figure out how to resolve this.
        numeric_cols = ['B', 'C', 'H', 'W', 'K', 'Filter', 'Stride']
        non_numeric_cols = ['Type', 'Class']

        # adding back in engine specific columns
        self.get_report_headers(csv1, unique_cols, numeric_cols, non_numeric_cols)
        self.get_report_headers(csv2, unique_cols, numeric_cols, non_numeric_cols)

        return self.generate_report(csv1,
                                    csv2,
                                    html,
                                    unique_cols,
                                    numeric_cols,
                                    non_numeric_cols,
                                    report_type='Network',
                                    report_name='Cache Residency',
                                    config=config,
                                    network=network)

    def generate_layer_stats_report(self, csv1, csv2, html, config='Unknown', network='Unkown'):

        unique_cols = ['Layer Idx', 'Layer Name']
        numeric_cols = [
            'Input Tensor Size (Ki)', 'Output Tensor Size (Ki)', 'Weight Size (Ki)', 'Total Size (Ki)', 'Filter Size',
            'Stride Size'
        ]
        non_numeric_cols = ['Layer Type', 'Input Tensor dims', 'Output Tensor Dims']

        # adding back in engine specific columns
        self.get_report_headers(csv1, unique_cols, numeric_cols, non_numeric_cols)
        self.get_report_headers(csv2, unique_cols, numeric_cols, non_numeric_cols)

        return self.generate_report(csv1,
                                    csv2,
                                    html,
                                    unique_cols,
                                    numeric_cols,
                                    non_numeric_cols,
                                    report_type='Network',
                                    report_name='Layer Summary',
                                    config=config,
                                    network=network)

    def get_report_headers(self, csv, unique, numeric, non_numeric):
        '''
        Function will attempt to sort out the headers of a CSV file for helping
        to generate at least some type of report for generic CSV reports. This
        can also be used by any report that will be dealing with a CSV file that
        has unpredictable headers.
        '''
        df = pd.read_csv(csv)
        columns = (c.rstrip() for c in df.columns.values)
        df = None

        for column in columns:

            # If the column already exists in one of the header categories do
            # not attempt to move it.
            if column in unique or column in numeric or column in non_numeric:
                continue

            # Building an exhaustive list of known unique column names. We hope
            # that at least one is present in the file we are checking.
            if column in [
                    'Network', 'Storage Option', 'Cache Size (Mi)', 'Layer Name', 'Layer Index', 'Layer Idx',
                    'Layer Number', 'Name'
            ]:
                unique.append(column)
            # Any column that contains these post-fixes is going to be some
            # form of decimal value.
            elif any(
                    column.endswith(contained) for contained in [
                        '(M)', '(Mi)', '(K)', '(Ki)', '(G)', '(Gi)', '(%)', '(Bpe)', 'Cycles', 'Util',
                        'Bytes Transferred', 'Efficiency', 'Num'
                    ]):
                numeric.append(column)
            # If all else fails, we will treat the column as a non-numeric.
            else:
                non_numeric.append(column)

        return unique, numeric, non_numeric

    def generate_generic_report(self,
                                csv1,
                                csv2,
                                html,
                                config='Unknown',
                                network='Unknown',
                                report_type=None,
                                report_name='Generic Report'):

        # Collecting all the common columns headers between both the reports.
        # We leave it up to the generate_report function to figure out that
        # there are issues with uncommon columns.
        unique_cols = []
        numeric_cols = []
        non_numeric_cols = []

        self.get_report_headers(csv1, unique_cols, numeric_cols, non_numeric_cols)
        self.get_report_headers(csv2, unique_cols, numeric_cols, non_numeric_cols)

        remove_rows = None

        if report_name == 'Generic Report':
            if 'avg_stencil_data' in html:
                report_name = 'Averge Stencil'
                remove_rows = ['AVG Stencil Use']
            elif 'classes_of_compute' in html:
                report_name = 'Classes of Compute'
                remove_rows = ['AVG Over Networks']
            elif 'total_layer_util_breakdown' in html:
                # Everything in this file is a numeric column. But because
                # they are just names of layers, there is no straight forward
                # way to figure this out. So we are going to cheat and just say
                # that all the non-numeric columns are the numeric columns. And
                # that there are no, non_numeric_cols.
                numeric_cols = non_numeric_cols
                non_numeric_cols = []
                report_name = 'Layer Breakdown'
                remove_rows = ['Total Breakdown']

        # If no report type was provided we will make our assumptions based
        # on the configuration and network names provided from the function
        # calling this function.
        if report_type is None:
            if config == '':
                report_type = 'Generic Report'
            elif network == '':
                report_type = 'Configuration'
            elif network == '0_config_files':
                report_type = 'Generic Report'
            else:
                report_type = 'Network'

        return self.generate_report(csv1,
                                    csv2,
                                    html,
                                    unique_cols,
                                    numeric_cols,
                                    non_numeric_cols,
                                    report_type=report_type,
                                    report_name=report_name,
                                    config=config,
                                    network=network,
                                    remove_row_indicies=remove_rows)

    def compare_statfiles(self, csv1, csv2, unique_cols, numeric_cols, non_numeric_cols, remove_row_indicies=None):
        differences = False

        # Get the CSV files
        r1h = pd.read_csv(csv1)
        r2h = pd.read_csv(csv2)

        # create a unique key from each row. This gives us an absolute indexing
        # beyond just placement in the file. This is a custom list per each
        # report we are viewing.
        if unique_cols:
            r1h.set_index(unique_cols, inplace=True, drop=True)
            r2h.set_index(unique_cols, inplace=True, drop=True)

        r1h.sort_index(inplace=True)
        r2h.sort_index(inplace=True)

        if remove_row_indicies is not None:
            r1h.drop(remove_row_indicies, inplace=True)
            r2h.drop(remove_row_indicies, inplace=True)

        # Merge and correct for issues preventing checks. This will deal with
        # differences in rows.
        merged = r1h.merge(r2h, indicator=True, how='outer', left_index=True, right_index=True)

        left_only = merged[merged['_merge'] == 'left_only']
        right_only = merged[merged['_merge'] == 'right_only']

        if len(left_only) > 0:
            r1h.drop(left_only.index, inplace=True)
            print('{} contains rows not found in {}:'.format(csv1, csv2))
            print('-' * 20)
            print(left_only)
            print('-' * 20)
            differences = True

        if len(right_only) > 0:
            r2h.drop(right_only.index, inplace=True)
            print('{} contains rows not found in {}:'.format(csv2, csv1))
            print('-' * 20)
            print(right_only)
            print('-' * 20)
            differences = True

        # This script does not do comparisons on columns that were not
        # requested. So we at minimum need to check that the requested columns
        # do exist. Then remove them from the checks coming up.
        r1h_remove_columns = [c for c in numeric_cols + non_numeric_cols if c not in r2h]
        r2h_remove_columns = [c for c in numeric_cols + non_numeric_cols if c not in r1h]

        # Remove columns missing in r2h from r1h
        if r1h_remove_columns:
            print('Expected columns {} are missing from CSV file {}'.format(r1h_remove_columns, csv2))
            r1h = r1h.drop(columns=list(r1h_remove_columns))
            differences = True

        # Remove columns missing in r1h from r2h
        if r2h_remove_columns:
            print('Expected columns {} are missing from CSV file {}'.format(r2h_remove_columns, csv1))
            r2h = r2h.drop(columns=list(r2h_remove_columns))
            differences = True

        for c in [c for c in numeric_cols if c not in r1h or c not in r2h]:
            numeric_cols.remove(c)

        for c in [c for c in non_numeric_cols if c not in r1h or c not in r2h]:
            non_numeric_cols.remove(c)

        # Any non-numeric columns we are going to fix the data types to strings.
        r1h[non_numeric_cols] = r1h[non_numeric_cols].astype(str)
        r2h[non_numeric_cols] = r2h[non_numeric_cols].astype(str)

        # Any numeric columns we are going to force to a non-NA value.
        # r1h[numeric_cols] = r1h[numeric_cols].fillna(0.0)
        # r2h[numeric_cols] = r2h[numeric_cols].fillna(0.0)

        static_column_order = numeric_cols + non_numeric_cols

        # If we are only expected to report when there are differences then
        # check if the files are the same or not first. If they are the same
        # the skip any further checks. This is a speed up for bigger diffs.
        if self.report_differences_only:
            try:
                diff_loc = r1h[static_column_order] != r2h[static_column_order]
                if not diff_loc.any(axis=None, skipna=False):
                    return None, differences
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as ex:
                raise Exception("Differences causing problems for pandas in files {} and {}.\nr1h: {}\nr2h: {}".format(
                    csv1, csv2, r1h, r2h))

        # Create a merged DataFrame with the indexing that was agreed between
        # r1h and r2h.
        merged = pd.DataFrame(index=r1h.index)

        # Create some headers for the numeric columns.
        numeric_cols_diff = [c + ' Difference' for c in numeric_cols]
        numeric_cols_perc = [c + ' Percentage Difference (%)' for c in numeric_cols]
        numeric_cols_pass = [c + ' Passed' for c in numeric_cols]
        r1_numeric_cols = [c + ' (csv1)' for c in numeric_cols]
        r2_numeric_cols = [c + ' (csv2)' for c in numeric_cols]
        # Calculate the differences and percentage differences of the requested
        # cells. Unfortunately due to quirks in pandas we have to repeat some
        # calculations because you cannot preform operations on dissimilar
        # dataframes. Its not enough to match size, the headers must match too.
        # This can be worked around by preforming per row operations. But this
        # leads to slower code.
        try:
            merged[r1_numeric_cols] = r1h[numeric_cols]
            merged[r2_numeric_cols] = r2h[numeric_cols]
            wrong_types_1 = [x for x in numeric_cols if r1h[x].dtype == object]
            wrong_types_2 = [x for x in numeric_cols if r2h[x].dtype == object]
            wrong_types_present = False
            if wrong_types_1:
                print('columns {} have non-numeric types in {}'.format(','.join(wrong_types_1), csv1))
            if wrong_types_2:
                print('columns {} have non-numeric types in {}'.format(','.join(wrong_types_2), csv2))
            if wrong_types_1 or wrong_types_2:
                raise TypeError('non-numeric types considered as numeric')
            merged[numeric_cols_diff] = r2h[numeric_cols] - r1h[numeric_cols]
            merged[numeric_cols_perc] = (r2h[numeric_cols] - r1h[numeric_cols]).abs() / (r1h[numeric_cols] +
                                                                                         r2h[numeric_cols]) * 200.0
            # Percentage difference checks can end up with N/A values due to divide
            # by 0 operations.
            merged.fillna(0.0, inplace=True)
            merged[numeric_cols_pass] = (merged[numeric_cols_perc] >=
                                         (-self.epsilon * 100)) & (merged[numeric_cols_perc] < (self.epsilon * 100))
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            raise Exception("Differences causing problems for pandas in files {} and {}".format(csv1, csv2))

        # Create some headers for the non-numeric columns.
        non_numeric_cols_diff = [c + ' Difference' for c in non_numeric_cols]
        non_numeric_cols_perc = [c + ' Percentage Difference (%)' for c in non_numeric_cols]
        non_numeric_cols_pass = [c + ' Passed' for c in non_numeric_cols]
        r1_non_numeric_cols = [c + ' (csv1)' for c in non_numeric_cols]
        r2_non_numeric_cols = [c + ' (csv2)' for c in non_numeric_cols]
        # Calculate the percentage difference and if the compared values passed
        # the threshold.
        try:
            merged[r1_non_numeric_cols] = r1h[non_numeric_cols]
            merged[r2_non_numeric_cols] = r2h[non_numeric_cols]
            merged[non_numeric_cols_diff] = r1h[non_numeric_cols] == r2h[non_numeric_cols]
            merged[non_numeric_cols_perc] = merged[non_numeric_cols_diff].replace({True: 0.0, False: 100.0})
            merged[non_numeric_cols_pass] = (merged[non_numeric_cols_perc] >=
                                             (-self.epsilon * 100)) & (merged[non_numeric_cols_perc] <
                                                                       (self.epsilon * 100))
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            raise Exception("Differences causing problems for pandas in files {} and {}".format(csv1, csv2))

        # Removing the indexing now that the comparisons are done. This places
        # the unique headers back into the data stream for reporting later on.
        merged.reset_index(inplace=True)

        # Generate an organized list of the headers to send the merged lists
        # off with out of the function.
        headers = unique_cols.copy()
        numeric_cols_merged = list(
            itertools.chain.from_iterable(
                zip(r1_numeric_cols, r2_numeric_cols, numeric_cols_diff, numeric_cols_perc, numeric_cols_pass)))
        non_numeric_cols_merged = list(
            itertools.chain.from_iterable(
                zip(r1_non_numeric_cols, r2_non_numeric_cols, non_numeric_cols_diff, non_numeric_cols_perc,
                    non_numeric_cols_pass)))

        headers.extend(numeric_cols_merged)
        headers.extend(non_numeric_cols_merged)

        r1h = None
        r2h = None

        return merged[headers], differences

    def generate_html_report(self, csv1filename, csv2filename, outfilename, diffs, unique_cols, numeric_cols,
                             non_numeric_cols):
        # Move the headers into the table data.
        # Convert the table to a JSON format.
        abs_table_string_json = diffs.T.reset_index().T.to_json(indent=4, orient='values')

        # Get a filtered list of the columns that end with the name Result.
        filtered_results = diffs.filter(regex=' Passed') == True
        # Rename the results to recover back the original list of headers
        filtered_results.rename(columns=lambda name: name.replace(' Passed', ''), inplace=True)
        # The result only true if all values are true in both axis.
        result = filtered_results.all(axis=None)

        # Get the column indexes in the original table for the numeric entries but just the Result entries.
        cmp_cols = [diffs.columns.get_loc(c + ' Percentage Difference (%)') for c in numeric_cols + non_numeric_cols]
        # Get the column indexes in the original table for the numeric entries.
        numeric_cols_list = [
            diffs.columns.get_loc(c + e) for c in numeric_cols for e in [' (csv1)', ' (csv2)', ' Difference']
        ]
        # Get the column indexes in the original table for the arrowed values.
        arrow_cols = [diffs.columns.get_loc(c + ' Difference') for c in numeric_cols]

        # Setup a summary table with the filtered results.
        frame = {
            'Total': len(diffs.index),
            'Passed': filtered_results.sum(axis=0),
            'Status': filtered_results.all(axis=0),
        }
        column_summary_table = pd.DataFrame(frame)
        # Remove column names from the index.
        column_summary_table.reset_index(inplace=True)
        # Rename the column from index to Colname
        column_summary_table.rename(columns={'index': 'Colname'}, inplace=True)
        # Convert the summary table to a JSON format.
        summary_table_string_json = column_summary_table.T.reset_index().T.to_json(indent=4, orient='values')

        filters = []
        filters.extend([[c, 'CategoryFilter'] for c in non_numeric_cols])
        filters.extend([[c, "NumberRangeFilter"] for c in numeric_cols])
        filter_desc_string_json = json.dumps(filters, indent=4)

        # Open the HTML template and replace specific values in the HTML.
        HTML_REPORT_TEMPLATE = self.template_dir + 'template-abench-cmpperf.html'
        with open(HTML_REPORT_TEMPLATE) as fin:
            report_template = '\n'.join([l.strip() for l in fin])
        outhtml = report_template
        outhtml = outhtml.replace('{{frozenColumns}}', str(len(unique_cols)))
        outhtml = outhtml.replace('{{csv1filename}}', csv1filename)
        outhtml = outhtml.replace('{{csv2filename}}', csv2filename)
        outhtml = outhtml.replace('{{result_final}}', 'PASSED' if result else 'FAILED')
        outhtml = outhtml.replace('{{epsilon_str}}', str(self.epsilon * 100) + '%')
        outhtml = outhtml.replace('{{abs_val_table}}', abs_table_string_json)
        outhtml = outhtml.replace('{{summary_table}}', summary_table_string_json)
        outhtml = outhtml.replace('{{numeric_cols}}', ','.join([str(y) for y in numeric_cols_list]))
        outhtml = outhtml.replace('{{percent_cols}}', ','.join([str(y) for y in cmp_cols]))
        outhtml = outhtml.replace('{{cmp_cols}}', ','.join([str(y) for y in cmp_cols]))
        outhtml = outhtml.replace('{{arrow_cols}}', ','.join([str(y) for y in arrow_cols]))
        outhtml = outhtml.replace('{{below_error_bar}}', ','.join([str(y) for y in ['null', -self.epsilon * 100]]))
        outhtml = outhtml.replace('{{error_bar}}',
                                  ','.join([str(y) for y in [-self.epsilon * 100, self.epsilon * 100]]))
        outhtml = outhtml.replace('{{above_error_bar}}', ','.join([str(y) for y in [self.epsilon * 100, 'null']]))
        outhtml = outhtml.replace('{{filter_desc}}', filter_desc_string_json)
        with open(outfilename, 'w') as fout:
            print(outhtml, file=fout)

        return result

    def generate_html_summary(self, dir1, dir2):
        summary = {
            'Generic': [['Workload', 'Type', 'Status', 'Report']],
            'Configuration': [['Workload', 'Type', 'Status', 'Report']],
            'Network': [['Workload', 'Config', 'Network', 'Type', 'Status', 'Report']],
        }

        for report in self.generated_reports:
            report_type = report['type']

            if report_type not in summary:
                report_type = 'Generic'

            columns = summary[report_type][0]
            row_value = []

            for column in columns:
                if column == 'Workload':
                    row_value.append('{} {}'.format(report['config'], report['network']))
                elif column == 'Config':
                    row_value.append(report['config'])
                elif column == 'Network':
                    row_value.append(report['network'])
                elif column == 'Type':
                    row_value.append(report['report'])
                elif column == 'Status':
                    row_value.append('PASSED' if report['result'] else 'FAILED')
                elif column == 'Report':
                    row_value.append('<a href="{}">Link</a>'.format(report['html'].replace(self.outdir, '.')))
                else:
                    raise Exception("Unknown column type {}".format(column))

            summary[report_type].append(row_value)

        summary_tbl_string_json = json.dumps(summary, indent=4)

        categories = json.dumps(list(summary.keys()))
        filters = json.dumps({category: summary[category][0] for category in summary})

        if len(self.inference_summary) > 0:
            self.inference_summary.reset_index(inplace=True)
            inference_summary_tbl_string_json = self.inference_summary.T.reset_index().T.to_json(indent=4,
                                                                                                 orient='values')
            cmp_cols_list = [
                self.inference_summary.columns.get_loc(c + ' Percentage Difference (%)')
                for c in self.inference_numeric_cols + self.inference_non_numeric_cols
            ]
            numeric_cols_list = [
                self.inference_summary.columns.get_loc(c + e) for c in self.inference_numeric_cols
                for e in [' (csv1)', ' (csv2)', ' Difference']
            ]
            arrow_cols_list = [
                self.inference_summary.columns.get_loc(c + ' Difference') for c in self.inference_numeric_cols
            ]
        else:
            headers = self.inference_unique_cols
            headers.extend(['Passed'])
            headers.extend([
                c + e for c in self.inference_numeric_cols
                for e in [' (csv1)', ' (csv2)', ' Difference', ' Percentage Difference (%)', ' Passed']
            ])
            headers.extend([
                c + e for c in self.inference_non_numeric_cols
                for e in [' (csv1)', ' (csv2)', ' Difference', ' Percentage Difference (%)', ' Passed']
            ])
            inference_summary_tbl_string_json = json.dumps([headers], indent=4)
            cmp_cols_list = []
            numeric_cols_list = []
            arrow_cols_list = []

        summary_filters = []
        summary_filters.extend([['Passed', 'CategoryFilter']])
        summary_filters.extend([[c, 'CategoryFilter'] for c in self.inference_non_numeric_cols])
        summary_filters.extend([[c, "NumberRangeFilter"] for c in self.inference_numeric_cols])
        filter_desc_string_json = json.dumps(summary_filters, indent=4)

        summary_outhtml_file = os.path.join(self.outdir, 'index.html')
        HTML_SUMMARY_REPORT_TEMPLATE = self.template_dir + 'template-abench-cmpperf-summary.html'
        with open(HTML_SUMMARY_REPORT_TEMPLATE) as fin:
            summary_report_template = '\n'.join([l.strip() for l in fin])
        summary_outhtml = summary_report_template
        summary_outhtml = summary_outhtml.replace('{{dir1name}}', dir1)
        summary_outhtml = summary_outhtml.replace('{{dir2name}}', dir2)
        summary_outhtml = summary_outhtml.replace('{{categories}}', categories)
        summary_outhtml = summary_outhtml.replace('{{filters}}', filters)
        summary_outhtml = summary_outhtml.replace('{{summary_table}}', summary_tbl_string_json)
        summary_outhtml = summary_outhtml.replace('{{epsilon_str}}', str(self.epsilon * 100) + '%')
        summary_outhtml = summary_outhtml.replace('{{frozenColumns}}', str(len(self.inference_unique_cols)))
        summary_outhtml = summary_outhtml.replace('{{below_error_bar}}',
                                                  ','.join([str(y) for y in ['null', -self.epsilon * 100]]))
        summary_outhtml = summary_outhtml.replace('{{error_bar}}',
                                                  ','.join([str(y) for y in [-self.epsilon * 100, self.epsilon * 100]]))
        summary_outhtml = summary_outhtml.replace('{{above_error_bar}}',
                                                  ','.join([str(y) for y in [self.epsilon * 100, 'null']]))
        summary_outhtml = summary_outhtml.replace('{{filter_desc}}', filter_desc_string_json)
        summary_outhtml = summary_outhtml.replace('{{inference_table}}', inference_summary_tbl_string_json)
        summary_outhtml = summary_outhtml.replace('{{percent_cols}}', ','.join([str(y) for y in cmp_cols_list]))
        summary_outhtml = summary_outhtml.replace('{{numeric_cols}}', ','.join([str(y) for y in numeric_cols_list]))
        summary_outhtml = summary_outhtml.replace('{{cmp_cols}}', ','.join([str(y) for y in cmp_cols_list]))
        summary_outhtml = summary_outhtml.replace('{{arrow_cols}}', ','.join([str(y) for y in arrow_cols_list]))

        with open(summary_outhtml_file, 'w') as fout:
            print(summary_outhtml, file=fout)

        return summary_outhtml_file


def mkoutdir(odir):
    if not os.path.exists(odir):
        os.makedirs(odir)
    else:
        sys.stderr.write("WARNING: output directory ({}) already exists!!".format(odir))


def get_next_level_dirs(idir, ignore_list):
    # return {d for d in os.listdir(idir) if os.path.isdir(os.path.join(idir,d)) and d != '0_config_files'}
    return {d for d in os.listdir(idir) if os.path.isdir(os.path.join(idir, d)) and d not in ignore_list}


def get_layer_stats(idir, d2):
    dd = os.path.join(idir, d2)
    xfs = [os.path.join(d2, d) for d in os.listdir(dd) if d.endswith('FS.csv')]
    xfsps = [os.path.join(d2, d) for d in os.listdir(dd) if d.endswith('FSPS.csv')]
    if not xfs:
        raise ValueError("At least one ({}) FS detailed-stats file in {} / {}!!".format(len(xfs), idir, d2))
    if not xfsps:
        raise ValueError("At least one ({}) FSPS detailed-stats file in {} / {}!!".format(len(xfsps), idir, d2))
    return (xfs[0], xfsps[0])


def check_file_exists(fl):
    if isinstance(fl, list):
        for f in fl:
            if not os.path.isfile(f):
                raise ValueError("{} does not exist!!".format(f))
    else:
        if not os.path.isfile(fl):
            raise ValueError("{} does not exist!!".format(fl))


def generate_file_report(csv1: str,
                         csv2: str,
                         html: str = None,
                         template_dir: str = 'tools/report_generator/',
                         epsilon: float = 1e-3,
                         output_dir: str = 'deleteme',
                         report_differences_only: bool = False):

    rp = ReportGenerator(template_dir=template_dir,
                         epsilon=epsilon,
                         output_dir=output_dir,
                         report_differences_only=report_differences_only)

    return rp.generate_file_report(csv1, csv2, html=html)


def generate_directory_report(dir1: str,
                              dir2: str,
                              dir_level: str = 'all',
                              dir_exact_match: bool = False,
                              template_dir: str = 'tools/report_generator/',
                              epsilon: float = 1e-3,
                              output_dir: str = 'deleteme',
                              report_differences_only: bool = False):

    rp = ReportGenerator(
        template_dir=template_dir,
        epsilon=epsilon,
        output_dir=output_dir,
        report_differences_only=report_differences_only,
    )

    rp.dir1 = dir1
    rp.dir2 = dir2
    rp.dir_exact_match = dir_exact_match

    if dir_level == 'all':
        differences = rp.generate_all_reports(dir1, dir2)
    elif dir_level == 'config':
        differences = rp.generate_config_reports(dir1, dir2)
    elif dir_level == 'network':
        differences = rp.generate_network_reports(dir1, dir2)

    report = rp.generate_html_summary(dir1, dir2)

    return differences, report


def main():
    cmdlineparser = argparse.ArgumentParser(description="Comparing Archbench Performance Reports")
    subparsers = cmdlineparser.add_subparsers(dest='subparser')
    fileparser = subparsers.add_parser('file', description='Comparing a single pair of reports(csv)')
    dirparser = subparsers.add_parser('dir',
                                      description='Comparing a single pair of directories(StaticInference, LayerStats)')

    cmdlineparser.add_argument('--epsilon',
                               '-e',
                               required=False,
                               default=1e-3,
                               type=float,
                               metavar='<error-bar>',
                               help="Error Bar(float), default=0.001, i.e. 0.1%%")
    cmdlineparser.add_argument('--templates', '-t', default='tools/report_generator/', help='Templates directory')
    cmdlineparser.add_argument('--differences_only',
                               action='store_true',
                               help='Only store and print when there are differences in the files.')

    fileparser.add_argument('--csv1',
                            '-c1',
                            required=True,
                            metavar='<perf-report-1>',
                            help="Archbench Peformance Report-1 (csv format)")
    fileparser.add_argument('--csv2',
                            '-c2',
                            required=True,
                            metavar='<perf-report-2>',
                            help="Archbench Peformance Report-2 (csv format)")
    fileparser.add_argument('--output', '-o', required=True, metavar='<outfile>', help="Output filename")

    dirparser.add_argument('--dir1',
                           '-d1',
                           default='golden_results/results-test-usecase/',
                           metavar='<perf-report-1>',
                           help="Archbench Peformance Report-1 (csv format)")
    dirparser.add_argument('--dir2',
                           '-d2',
                           default='results/',
                           metavar='<perf-report-2>',
                           help="Archbench Peformance Report-2 (csv format)")
    dirparser.add_argument('--output', '-o', required=True, metavar='<outdir>', help="Output dirname")
    dirparser.add_argument('--dir_level',
                           '-l',
                           default='all',
                           choices=['all', 'config', 'network'],
                           metavar='<dir-level>',
                           help='''
    Help the script figure out what level of checks are happening for scanning directories.
    all - The directories provided were the root results directories.
    config - The directories provided were the configuration specific directories.
    network - The directories provided were the network specific directories.
                           ''')
    dirparser.add_argument('--dir_exact_match',
                           action='store_true',
                           help='If set dir1 and dir2 directories are expected to be identical')

    if len(sys.argv) <= 1:
        cmdlineparser.print_help(sys.stderr)
        sys.exit(1)
    cmdlineargs = cmdlineparser.parse_args()

    tdir = cmdlineargs.templates
    eps = float(cmdlineargs.epsilon)
    output = cmdlineargs.output

    if cmdlineargs.subparser == 'file':
        odir, _ = os.path.split(output)
        if odir == '':
            odir = '.'
    else:
        odir = output

    mkoutdir(odir)

    if cmdlineargs.subparser == 'file':
        differences = generate_file_report(csv1=cmdlineargs.csv1,
                                           csv2=cmdlineargs.csv2,
                                           html=output,
                                           template_dir=tdir,
                                           epsilon=eps,
                                           output_dir=odir,
                                           report_differences_only=cmdlineargs.differences_only)

    else:
        differences, report = generate_directory_report(dir1=cmdlineargs.dir1,
                                                        dir2=cmdlineargs.dir2,
                                                        dir_level=cmdlineargs.dir_level,
                                                        dir_exact_match=cmdlineargs.dir_exact_match,
                                                        template_dir=tdir,
                                                        epsilon=eps,
                                                        output_dir=odir,
                                                        report_differences_only=cmdlineargs.differences_only)

        if differences:
            print('Differences found between {} and {}. Check report {}'.format(cmdlineargs.dir1, cmdlineargs.dir2,
                                                                                report))
        else:
            print('All checks passed between {} and {}. View report {}'.format(cmdlineargs.dir1, cmdlineargs.dir2,
                                                                               report))

    return differences


if __name__ == "__main__":
    exit(main())
