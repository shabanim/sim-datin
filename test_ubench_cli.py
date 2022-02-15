import os
import subprocess
import tempfile
import yaml

from unittest import TestCase

expected_scaleup_output = './modelzoo/ubench/ubench.prototxt_graph_out.json\n' \
                  'Scaleup time(ms) : {}\nScaleout time(ms): 0.0\n'

expected_scaleout_output = './modelzoo/ubench/ubench.prototxt_graph_out.json\n'\
                            'Scaleup time(ms) : {}\n' \
                            'Scaleout time(ms): {}\n'

knobs_file = './modelzoo/base_param_cfg.yml'

class TestUbenchCli(TestCase):
    """
    Test case to perform regression of param-runner
    """

    def update_scaleup_topology(self, network, dest_file):
        file = open(knobs_file)
        knobs = yaml.safe_load(file)
        file.close()
        knobs["Collective"]["scale_up_collectiveAlgo"]["nw_topology"] = network
        file_dest = open(dest_file, 'w')
        yaml.dump(knobs, file_dest)
        file_dest.close()

    def update_scaleout_topology(self, network, dest_file):
        file = open(knobs_file)
        knobs = yaml.safe_load(file)
        file.close()
        knobs["Collective"]["scale_out_collectiveAlgo"]["nw_topology"] = network
        file_dest = open(dest_file, 'w')
        yaml.dump(knobs, file_dest)
        file_dest.close()

    def disable_scaleout(self, dest_file):
        file = open(dest_file)
        knobs = yaml.safe_load(file)
        file.close()
        knobs["Comms"]["scale_out"]["enabled"] = False
        file_dest = open(dest_file, 'w')
        yaml.dump(knobs, file_dest)
        file_dest.close()

    def test_ubench_Ring_AllReduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allreduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.47682016907793207
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Ring_AllGather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allgather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.24191008453896604
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Ring_Gather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'gather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.24191008453896604
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Ring_ReduceScatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reducescatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.24191008453896604
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Ring_Scatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'scatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.24191008453896604
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Ring_Reduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.520241699845679
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Ring_Broadcast(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("ring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'broadcast',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.520241699845679
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_AllReduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allreduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.30766657677469134
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_All2All(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'a2a',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.30766657677469134
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_AllGather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allgather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15733328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_Gather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'gather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15733328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_ReduceScatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reducescatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15733328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_Scatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'scatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15733328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_Reduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3357561657848324
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_P2P_Broadcast(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'broadcast',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3357561657848324
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_AllReduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allreduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.29550431139081784
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_AllGather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allgather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15125215569540895
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_Gather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'gather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15125215569540895
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_ReduceScatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reducescatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15125215569540895
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_Scatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'scatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.15125215569540895
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_Reduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3130235767746914
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_BidirRing_Broadcast(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("bidirring", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'broadcast',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3130235767746914
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_AllReduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allreduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.34678293061985593
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_AllGather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allgather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.17689146530992797
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_Gather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'gather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.17689146530992797
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_ReduceScatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reducescatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.17689146530992797
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_Scatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'scatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.17689146530992797
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_Reduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3775162844650206
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Hypercube_Broadcast(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("hypercube", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'broadcast',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3775162844650206
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_AllReduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allreduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.32598657677469134
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_AllGather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'allgather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.16649328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_Gather(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'gather',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.16649328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_ReduceScatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reducescatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.16649328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_Scatter(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'scatter',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.16649328838734567
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_Reduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'reduce',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3843862844650206
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Torus3d_Broadcast(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("torus3d", tmpfile)
        self.disable_scaleout(tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'broadcast',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3843862844650206
        self.assertEqual(stdout.decode("utf-8"), expected_scaleup_output.format(scaleup_time))
        os.unlink(tmpfile)

    def test_ubench_Flat_Allreduce(self):
        fd, tmpfile = tempfile.mkstemp(suffix='.yaml')
        os.close(fd)
        self.update_scaleup_topology("p2p", tmpfile)
        self.update_scaleout_topology("flat", tmpfile)
        print(tmpfile)
        cmd = [
            'python', './micro_service/dl-modelling.py', 'ubench',
            '-m', '52428800',
            '-a', 'a2a',
            '-c', '{}'.format(tmpfile)
        ]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        stdout, _ = p.communicate()
        scaleup_time = 0.3357561657848324
        scaleout_time = 0.3632
        self.assertEqual(stdout.decode("utf-8"), expected_scaleout_output.format(scaleup_time, scaleout_time))
        os.unlink(tmpfile)


if __name__ == '__main__':
    import unittest
    unittest.main()
