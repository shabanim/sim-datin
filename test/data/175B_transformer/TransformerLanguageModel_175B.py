from abench.graph.network import Network
from abench.scripts.network_scripts.TransformerEncoder import TransformerEncoder
from abench.ops import Tensor, layer_factory
import math


class TransformerLanguageModel_175B(Network):
    def __init__(
            self,
            name,
            input_seq_len=2048,  # length of input sequence
            hidden_act='relu',  # Supports "relu" and "gelu"
            d_k=128,  # Dimensions of query and key inputs (section 3.2.1)
            d_v=128,  # Dimensions of value inputs (section 3.2.1)
            d_model=12288,  # Model dim (section 3.1)
            d_ff=49152,  # For full model - FFN inner layer dimension (section 3.3)
            num_enc_layers=1,  # Num of encoder layers
            num_heads=96,  # For full model - Num of attention heads (h, section 3.2.2)
            vocab_size=50280,  # For full model - Size of vocabulary in token embedding
            head_divide=16,  # Dividing factor for num_heads (model parallelism)
            d_ff_divide=16,  # Dividing factor for d_ff (model parallelism)
            vocab_divide=16,  # Dividing factor for vocab_size (model parallelism)
            verbose=False,
            userInput=None):
        '''
        This is the Transformer Language model to be used for training.
        See explanation of parameters in "Attention is all you Need, Vaswani, et al" https://arxiv.org/pdf/1706.03762.pdf

        The specific parameters values selected above follow the GPT3 Paper (Table2.1) - "Language
        Models are Few-Shot Learners" https://arxiv.org/abs/2005.14165
        '''
        self.input_seq_len = input_seq_len
        self.hidden_act = hidden_act
        self.d_k = d_k
        self.d_v = d_v
        self.d_model = d_model
        self.d_ff_per_tile = math.ceil(d_ff / d_ff_divide)  # Per tile
        self.num_heads_per_tile = math.ceil(num_heads / head_divide)  # Per tile
        self.num_enc_layers = num_enc_layers
        self.vocab_size_per_tile = math.ceil(vocab_size / vocab_divide)  # Per tile
        super().__init__(name, verbose, userInput=userInput)

    def create(self):
        encoder_input_indices = Tensor.from_dims("encoder_input_tensor", (self.batch, self.input_seq_len, 1, 1))
        self.addInputTensor(encoder_input_indices, override_batch=False)
        # TODO: Add embedding table as input to Embed and decode_to_logits layer. Keeping the following line here and commented
        # embedding_table = Tensor.from_dims("embedding_table", (1,1, self.vocab_size_per_tile, self.d_model))

        # Token embedding encoder
        encoder_token_embed = self.add(
            layer_factory.get_layer("Embed",
                                    "encoder_token_embedding", [encoder_input_indices],
                                    params={
                                        "num_output": self.d_model,
                                        "input_dim": self.vocab_size_per_tile
                                    }))  # TODO: add embedding_table=embedding_table
        encoder_token_embedding_out = self.add(
            layer_factory.get_layer("Reshape",
                                    "encoder_token_embedding_out",
                                    encoder_token_embed,
                                    params={"reshape_param": [0, 0, self.d_model, -1]}))
        encoder_in = encoder_token_embedding_out

        encoder = TransformerEncoder(name='transformer_encoder',
                                     input_tensor=encoder_in,
                                     d_k=self.d_k,
                                     d_v=self.d_v,
                                     d_model=self.d_model,
                                     d_ff=self.d_ff_per_tile,
                                     num_heads=self.num_heads_per_tile,
                                     hidden_act=self.hidden_act,
                                     num_layers=self.num_enc_layers,
                                     batch=self.batch,
                                     userInput=None)
        self.add_subnetwork(encoder)

        encoder_out = encoder.out
        activationOutput = self.add(layer_factory.get_layer("Softmax", "FinalSoftmax", encoder_out))

        return activationOutput
