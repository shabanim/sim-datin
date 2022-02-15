from math import ceil
from networks.BERT_Base import BERT_Base
from abench.ops import Tensor, layer_factory


class BERT_Large_Pretraining(BERT_Base):
    def __init__(
            self,
            name,
            input_seq_len=512,  # Length of each input seq
            d_model=1024,  # Model dimension
            num_enc_layers=24,  # Num of encoder layers
            num_heads=16,  # Num of attention heads
            vocab_size=30522,  # Size of the vocabulary
            perc_masked=0.15,  # % tokens masked out of the input seq
            verbose=False,
            userInput=None):
        self.perc_masked = perc_masked
        super().__init__(name, input_seq_len, d_model, num_enc_layers, num_heads, vocab_size, verbose, userInput)

    def create(self):
        super().create()

        # Masked LM output (MLM)

        # batch_size = self.encoder_out.batch
        num_masked = ceil(self.input_seq_len * self.perc_masked)
        self.addInputTensor(Tensor.from_dims("masked_token_indices", [self.batch, num_masked, 1, 1]),
                            override_batch=False)
        # mlm_gather_indices = self.add(Reshape('mlm_indices', self.input_tensors[3], [batch_size*self.input_tensors[3].channel,1,1,1]))
        # gather = self.add(Gather('mlm_gather_masked', [mlm_gather_indices], data_dict=[batch_size*self.input_seq_len, self.d_model]))
        # mlm_masked_tokens = self.add(Reshape('gathered_masked_tokens', gather, [batch_size, num_masked, self.d_model,-1]))

        mlm_tfgather = self.add(
            layer_factory.get_layer("GatherFromTensor", 'mlm_tfgather_masked',
                                    [self.encoder_out, self.input_tensors[3]], None, {'axis': 1}))

        # Dense
        dense_params = {'num_output': self.d_model, 'input_tensor_rank': 3, 'weight': None}
        transform = self.add(layer_factory.get_layer("Dense", 'mlm_transform', [mlm_tfgather], None, dense_params))

        transform_gelu = self.add(layer_factory.get_layer("Gelu", 'mlm_transform_gelu', transform))
        # LayerNorm
        mlm_layernorm = self.add(
            layer_factory.get_layer("LayerNorm", "mlm_layernorm", [transform_gelu], None, {'norm_axis': 2}))

        # MatMul + BiasAdd
        # TODO: Currently modeling as Dense. But these "weights" are same as
        # the full embedding table and need to reflect during training as such
        dense_params = {'num_output': self.vocab_size, 'input_tensor_rank': 3, 'weight': None}
        vocab_project = self.add(
            layer_factory.get_layer("Dense", 'mlm_vocab_project', [mlm_layernorm], None, dense_params))
        vocab_project_biasadd = self.add(layer_factory.get_layer("Bias", 'mlm_vocab_project_biasadd', [vocab_project]))

        # MLM Softmax
        vocab_log_probs = self.add(layer_factory.get_layer("SoftMax", 'mlm_softmax_logprobs', [vocab_project_biasadd]))

        # Next Sentence Loss (NS)
        self.addInputTensor(Tensor.from_dims("select_pooled", [self.batch, 1, 1, 1]), override_batch=False)
        ns_tfgather = self.add(
            layer_factory.get_layer("GatherFromTensor", 'ns_tfgather_pooled', [self.encoder_out, self.input_tensors[4]],
                                    None, {'axis': 1}))
        dense_params = {'num_output': 1024, 'input_tensor_rank': 3, 'weight': None}
        pooler = self.add(layer_factory.get_layer("Dense", 'pooler_dense', [ns_tfgather], None, dense_params))
        pooler_tanh = self.add(layer_factory.get_layer("Tanh", 'pooler_tanh', [pooler]))
        dense_params = {'num_output': 2, 'input_tensor_rank': 3, 'weight': None}
        ns_project = self.add(layer_factory.get_layer("Dense", 'ns_project', [pooler_tanh], None, dense_params))
        ns_project_biasadd = self.add(layer_factory.get_layer("Bias", 'ns_project_biasadd', [ns_project]))

        # Softmax
        ns_log_probs = self.add(layer_factory.get_layer("SoftMax", 'ns_softmax_logprobs', [ns_project_biasadd]))
