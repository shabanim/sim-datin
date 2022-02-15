"""
Script can be used to:
    - list operations in TF models
    - Freeze model
    - Save model as graph
Input model types:
    - Protobuf (.pb) model
    - SavedModel model
    - Checkpoint
Outputs: (dependent of chosen mode)
    - TXT file listing all operations to allow user to find input tensors and output nodes
    - Frozen model
    - Graph of model
"""

import os
import warnings
warnings.simplefilter("ignore", category=DeprecationWarning)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import argparse
from pathlib import Path
import sys
import tensorflow as tf
# from tensorflow.python.tools import freeze_graph
# from tensorflow.core.protobuf import saver_pb2
# import tensorflow.contrib
from tensorflow.python.saved_model import tag_constants
from tensorflow.python.summary import summary
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

os.environ['PYTHONHASHSEED'] = '0'

if sys.version_info[:2] < (3, 5):
    raise Exception("Minimum of Python 3.5 required")


# Get arguments
def get_args():
    def instr2bool(in_value):
        if in_value.lower() in ['true', 't']:
            return True
        else:
            return False

    parserobj = argparse.ArgumentParser(add_help=False)

    # IMPORTANT parameters
    group_req = parserobj.add_argument_group('IMPORTANT ARGUMENTS')
    group_req.add_argument('--model_dir',
                           type=lambda s: Path(s),
                           default='networks/',
                           help='Directory of models. Default:models/')
    group_req.add_argument('--model', type=str, default=None, dest='model', help='File containing model topology')
    group_req.add_argument(
        "--mode",
        type=str.lower,
        dest='mode',
        required=True,  #  default='list_ops',
        choices=['list_ops', 'freeze_model', 'save_graph'],
        help="list_ops: List operations in checkpoint directory and print to file\n" +
        "freeze_model: Freeze TF model\n" + "save_graph: Save checkpoint/savedmodel to graph (pb)")

    # FREEZE_MODEL optional parameters
    group_freeze_model = parserobj.add_argument_group('OPTIONAL FREEZE_MODEL ARGUMENTS')
    group_freeze_model.add_argument('--h', '--help', action='help')
    group_freeze_model.add_argument('--input_tensor',
                                    type=str,
                                    default="",
                                    help='The name(s) of the input tensors, comma separated.')
    group_freeze_model.add_argument('--output_node',
                                    type=str,
                                    default="",
                                    help='The name(s) of the output nodes, comma separated.')

    # TF SPECIFIC ARGUMENTS
    group_tf = parserobj.add_argument_group('OPTIONAL TF SPECIFIC ARGUMENTS')
    group_tf.add_argument(
        '--savedmodel',
        type=instr2bool,
        default=False,
        const=True,  # action='store_true',
        nargs='?',
        help='Set to True if model is a savedmodel directory')
    group_tf.add_argument('--signature_def',
                          default='serving_default',
                          type=str,
                          help='signature_def for TF SavedModels')
    group_tf.add_argument('--frozen_suffix',
                          type=str,
                          default=None,
                          help='Suffix to add to frozen graph filename [<model_name>_<frozensuffix>.frozen.pb')

    # Store and use arguments
    args = parserobj.parse_args()

    if not args.model:
        raise ValueError("Please specify file/directory containing model topology (--model)")

    if args.mode == 'save_graph' and args.model.endswith('.pb'):
        raise ValueError("Please provide checkpoint/savedmodel directory in order to save as graph (pb)")

    setattr(args, 'model', Path.cwd() / args.model_dir / args.model)

    # Create directories for results and logs
    args.result_dir = Path.cwd() / 'results'
    return args


def load_nn(in_params):
    if in_params.model.suffix == '.pb':
        this_graph_def = tf.GraphDef()
        with in_params.model.open(mode='rb') as f:
            this_graph_def.ParseFromString(f.read())
        tf.compat.v1.reset_default_graph()
        with tf.compat.v1.Session(graph=tf.import_graph_def(this_graph_def, name='')) as session:
            my_graph = session.graph
    elif in_params.savedmodel and in_params.model.suffix == "":
        # Make session and load SavedModel
        with tf.compat.v1.Session(graph=tf.Graph()) as session:
            # session = tf.compat.v1.Session(graph=tf.Graph())
            tf.compat.v1.saved_model.loader.load(session, [tag_constants.SERVING], str(in_params.model))
            my_graph = session.graph
    elif in_params.model.suffix == "":
        meta_files = [str(f.stem) for f in list(in_params.model.glob('**/*.meta'))]
        checkpoint_state = tf.train.get_checkpoint_state(str(in_params.model))
        if checkpoint_state and checkpoint_state.model_checkpoint_path:
            ckpt_file = os.path.basename(checkpoint_state.model_checkpoint_path)
        elif len(meta_files) > 0:
            ckpt_file = meta_files[0]
        else:
            raise ImportError('[!] Failure loading checkpoint state')
        meta_file = ckpt_file + '.meta'
        with tf.compat.v1.Session() as session:
            session.run(tf.compat.v1.global_variables_initializer())
            saver = tf.compat.v1.train.import_meta_graph(str(in_params.model / meta_file), clear_devices=True)
            saver.restore(session, str(in_params.model / ckpt_file))
            my_graph = session.graph
    else:
        raise ValueError('tf model file must be a pb file, checkpoint directory, or savedmodel directory.')
    return my_graph


def list_network_ops(in_params, my_graph):
    def get_operation_info(attr):
        for m in getattr(n, attr):
            try:
                shape = 'unknown' if m.get_shape() == None else str(m.get_shape().as_list())
                print('\t' + attr.upper() + ' NAME: ' + m.name + ' \tSHAPE: ' + shape + ' \tDTYPE: ' + m.dtype.name,
                      file=log_file)
            except ValueError:
                print('\t' + attr.upper() + ' NAME: ' + m.name + ' \tDTYPE: ' + m.dtype.name, file=log_file)

    file_name = str(in_params.result_dir / 'LISTOPS_{}.txt'.format(in_params.model.stem))
    with open(file_name, 'w') as log_file:
        for n in my_graph.get_operations():
            print('OPERATION NAME: ' + n.name, file=log_file)
            print('\tTYPE NAME: ' + n.type, file=log_file)
            # Get io info
            get_operation_info('inputs')
            get_operation_info('outputs')
    print('[!] List of ops for {} located in {}'.format(str(in_params.model), file_name))


def freeze_model(in_params, my_graph):
    def adjust_graphdef(curr_graph_def):
        # Remove unused nodes
        from tensorflow.tools.graph_transforms import TransformGraph
        # transforms = ["strip_unused_nodes", "fold_constants(ignore_errors=true)", "fold_batch_norms",
        #               "fold_old_batch_norms", "remove_nodes(op=Identity, op=CheckNumerics)",
        #               "sort_by_execution_order"]
        transforms = ["strip_unused_nodes", "fold_batch_norms", "fold_old_batch_norms", "sort_by_execution_order"]
        # transforms = ["sort_by_execution_order"]
        new_graph_def = TransformGraph(curr_graph_def, in_params.input_tensor.split(','),
                                       in_params.output_node.split(','), transforms)

        for node in new_graph_def.node:
            node.device = ''
            if node.op == 'RefSwitch':
                node.op = 'Switch'
                for index in range(len(node.input)):
                    if 'moving_' in node.input[index]:
                        node.input[index] = node.input[index] + '/read'
            elif node.op == 'AssignSub':
                node.op = 'Sub'
                if 'use_locking' in node.attr:
                    del node.attr['use_locking']
            elif node.op == 'AssignAdd':
                node.op = 'Add'
                if 'use_locking' in node.attr:
                    del node.attr['use_locking']
        return new_graph_def

    tf.compat.v1.reset_default_graph()
    with tf.compat.v1.Session(graph=my_graph) as session:
        input_graph_def = adjust_graphdef(my_graph.as_graph_def())
        session.run(tf.compat.v1.tables_initializer())
        session.run(tf.compat.v1.global_variables_initializer())
        output_graph_def = tf.compat.v1.graph_util.convert_variables_to_constants(
            session,  # The session is used to retrieve the weights
            input_graph_def,  # The graph_def is used to retrieve the nodes
            in_params.output_node.split(',')  # The output node names are used to select the useful nodes
        )

        # Serialize and dump the output graph to the filesystem
        # Writes frozen graph outside of checkpoint folder
        if in_params.model.is_dir():
            frozen_graph_file = str(in_params.model) + '.frozen.pb'
        else:
            frozen_graph_file = str(in_params.model.with_name(in_params.model.stem + '.frozen.pb'))

        if in_params.frozen_suffix is not None:
            frozen_graph_file = frozen_graph_file.replace('.frozen.pb', '_' + in_params.frozen_suffix + '.frozen.pb')

        with tf.io.gfile.GFile(frozen_graph_file, 'wb') as f:
            f.write(output_graph_def.SerializeToString())

        if not os.path.isfile(frozen_graph_file):
            assert FileExistsError('[!] Saving frozen graph failed')
        print('[!] Frozen graph for {} located in {}'.format(str(in_params.model), frozen_graph_file))
        print('[!] PLEASE USE FROZEN GRAPH FOR ANALYSIS')
        sys.exit(0)


def save_graph(in_params, my_graph):
    if in_params.model.is_dir():
        graph_file = str(in_params.model) + '.graph.pb'
    else:
        graph_file = str(in_params.model.with_name(in_params.model.stem + '.graph.pb'))

    with tf.compat.v1.Session(graph=my_graph) as session:
        with tf.io.gfile.GFile(graph_file, 'wb') as f:
            f.write(session.graph.as_graph_def().SerializeToString())

    filewriter = summary.FileWriter(str(in_params.model), graph=my_graph)
    if not os.path.isfile(graph_file):
        assert FileExistsError('[!] Saving graph failed')
    print('[!] Graph for {} located in {}'.format(str(in_params.model), graph_file))
    print('[!] Event file for tensorboard in {}'.format(str(in_params.model), graph_file))
    sys.exit(0)


def main(input_args):
    my_graph = load_nn(input_args)

    if input_args.mode == 'freeze_model':
        freeze_model(input_args, my_graph)
    elif input_args.mode == 'save_graph':
        save_graph(input_args, my_graph)
    else:
        list_network_ops(input_args, my_graph)


if __name__ == "__main__":
    in_params = get_args()
    main(in_params)
