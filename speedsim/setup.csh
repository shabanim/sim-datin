#!/bin/tcsh -f

if ( ! $?SPEEDSIM_DIR ) then
    setenv SPEEDSIM_DIR "/p/dpg/arch/perfhome/speedsim/latest/"
endif

setenv CONDUIT_PATH "/p/dpg/arch/perfhome/pyconduit/latest"
if ( $?PYTHONPATH ) then
    setenv PYTHONPATH "${PYTHONPATH}:${CONDUIT_PATH}:${SPEEDSIM_DIR}"
else
    setenv PYTHONPATH "${CONDUIT_PATH}:${SPEEDSIM_DIR}"
endif

setenv NEMO_PATH "/p/dpg/arch/perfhome/nemo/latest/power_management/"
source $NEMO_PATH/setup.csh
setenv PATH "/p/dpg/arch/perfhome/python/miniconda3/bin/:${PATH}"
setenv PATH "/p/dpg/arch/perfhome/python/miniconda37/pkgs/graphviz-2.40.1-h21bd128_2/bin/:${PATH}"
