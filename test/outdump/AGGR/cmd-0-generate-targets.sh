python /home/sdg3/param/param_zero_inf_rebase/dl-modeling/ab-release-automation/generate_targets.py -g /home/sdg3/param/param_zero_inf_rebase/dl-modeling/test/data/Gen12-SKUs-PVC.xlsx -w /home/sdg3/param/param_zero_inf_rebase/dl-modeling/test/data/PVC-Workloads.xlsx -i FALSE -t TRUE --compderate 0.95 --fusion workload --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE --frequency 1400 1500 100 -o test/outdump -s AGGR -a run --filtersku PVC1T-512-C0-85-80 --filter TransformerLanguageModel_1T_zinf --dump_html
