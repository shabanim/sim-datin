python /home/sdg3/param/param_zero_inf_rebase/dl-modeling/ab-release-automation/run_gen_jobs.py --wait -d test/outdump/AGGR/Devices.csv -w /home/sdg3/param/param_zero_inf_rebase/dl-modeling/test/data/PVC-Workloads.xlsx --abroot /home/sdg3/param/param_zero_inf_rebase/dl-modeling/ab-release-automation/smab -m test/outdump/AGGR/AGGR-map.csv -o test/outdump/AGGR -l AGGR -r run -f TransformerLanguageModel_1T_zinf --bwdfusion False --no-layerflush --pipeline-backward-pass TRUE --flush-oversized-output-tensor TRUE --dump_html