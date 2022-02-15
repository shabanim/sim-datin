import yaml
from collections import OrderedDict


class Knobs(OrderedDict):
    def __init__(self, config_file,  ab_config=None):
        with open(config_file) as file:
            knobs = yaml.safe_load(file)


        if ab_config:
            with open(ab_config) as file:
                knobs_AB = yaml.safe_load(file)
            knobs['Device']['frequency_in_Ghz'] = (knobs_AB['Device']['deviceFreq'][0]/1000000000)
            knobs['Device']['batch_size'] = (knobs_AB['Device']['layerBatches'])


        if knobs:
            self._network_knobs = Knobs.get_network_knobs(knobs)
            self._collective_knobs = knobs["Collective"]

    def __getitem__(self, key):
        if key in self.network_knobs.keys():
            return self.network_knobs[key]
        elif key in self.collective_knobs.keys():
            return self.collective_knobs[key]
        raise KeyError(key)

    @property
    def network_knobs(self):
        return self._network_knobs

    @property
    def collective_knobs(self):
        return self._collective_knobs

    @staticmethod
    def get_network_knobs(knobs):
        network_knobs = {}
        network_knobs.update(knobs["Device"])
        network_knobs.update({"so_" + k: v for (k, v) in knobs["Comms"]["scale_out"].items()})
        knobs["Comms"].pop("scale_out")
        network_knobs.update({"su_" + k: v for (k, v) in knobs["Comms"]["scaleup"].items()})
        knobs["Comms"].pop("scaleup")
        network_knobs.update({"sw_" + k: v for (k, v) in knobs["Comms"]["software"].items()})
        knobs["Comms"].pop("software")
        network_knobs.update(knobs["Comms"])
        return network_knobs
