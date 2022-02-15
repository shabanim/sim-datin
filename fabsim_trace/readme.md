## Fabsim run log parsing for comms annotation

- AB+Param+Fabsim+SpeedSim is a two step process
    - Geneate run simulation log (scaleup and scaleout) for a trace (with MP,DP,T configs) using fabsim
    - Use run logs along with trace and ABs graph output to generate overlap analysis with speedsim

- Below readme shows how to generate Overlap analysis using SpeedSim

- Generic command to enable flow
    - additional parameters to be given along with parameter of summary commands
        - --fabsim_trace FABSIM_TRACE
        - --fabsim_scaleup_run_log FABSIM_SCALEUP_RUN_LOG
        - --fabsim_scaleout_run_log FABSIM_SCALEOUT_RUN_LOG
    - run_logs are usually called ``` run_simulation.log ``` in fabsim
```
(dlmodel) /dl-modeling >>> python ./micro_service/dl-modelling.py summary -f ./archbench/networks/<network>.py -cf ./archbench/configs/<config>.yaml -c ./modelzoo/base_param_cfg.yml --fabsim_trace ./fabsim_trace/<trace>.json --fabsim_scaleup_run_log <path>/run_scaleup_simulation.log --fabsim_scaleout_run_log <path>/run_scaleup_simulation.log -o ./modelzoo/Report.csv --training --trg-greedy-flush True --trg-optimizer sgd --dump_html -ssd
```

- sample run using transformer 100B network
```
(dlmodel) /dl-modeling >>> python ./micro_service/dl-modelling.py summary -f ./archbench/networks/TransformerLanguageModel_100B.py -cf ./archbench/configs/GEN_PVC1T.yaml -c ./modelzoo/base_param_cfg.yml --fabsim_trace ./fabsim_trace/transformer_100B/T128_MP16_DP8_LM_100B.json --fabsim_scaleup_run_log ./fabsim_trace/transformer_100B/run_scaleup_simulation.log --fabsim_scaleout_run_log ./fabsim_trace/transformer_100B//run_scaleout_simulation.log -o ./modelzoo/Report.csv  --training --trg-greedy-flush True --trg-optimizer sgd --dump_html -ssd
```