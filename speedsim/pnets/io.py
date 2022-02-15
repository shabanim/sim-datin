from .simulation import (NAN, SIM_EVENT_DURATION, SIM_EVENT_FINISH,
                         SIM_EVENT_RESOURCE, SIM_EVENT_RESOURCE_IDX,
                         SIM_EVENT_START, SIM_EVENT_TRANSITION)


def sim_results_to_trace_event(sim_results):
    """
    Convert simulation results DataFrame to TraceEvent format (JSON).
    See google's doc on "Trace Event Format" for more details.
    :param sim_results: pandas.DataFrame with results of simulation
    :return: JSON

    NOTE: resource names and transition names are interpreted to recognize '.' as a feature/sub-block separator.
    """
    events = []

    # features have resource names separated by dots
    filtered = sim_results[[SIM_EVENT_START, SIM_EVENT_FINISH, SIM_EVENT_TRANSITION, SIM_EVENT_RESOURCE,
                            SIM_EVENT_RESOURCE_IDX, SIM_EVENT_DURATION]]

    for start_time, finish_time, tran, resource, resource_idx, duration in filtered.itertuples(index=False):
        if '.' in resource:
            resource, feature = resource.split('.')
        else:
            feature = 'BUSY'

        name = tran.split('.')[-1]

        if duration == NAN:
            duration = 0

        events.append({
            'name': name,
            'cat': 'execution',
            'ph': 'X',
            'pid': resource + '_' + str(resource_idx),
            'tid': feature,
            'ts': float(start_time),
            'dur': float(duration)
        })

    return {
        'traceEvents': events,
        'displayTimeUnit': 'ns',
        "systemTraceEvents": "SystemTraceData",
        "otherData": {},
    }
