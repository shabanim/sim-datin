from abench.ops import Tensor, layer_factory
from abench.graph.network import Network


class DLRM_inference_mlperf(Network):
    def __init__(self,
                 name,
                 input_seq_len=1,
                 global_batch=55296/32,
                 local_batch_size=55296/32,
                 d_model=128,
                 vocab_size=40000000,
                 verbose=False,
                 no_embedding_local=32/32,
                 no_embedding_total=32,
                 denseinputfeatures=13,
                 offset=-1,
                 top_mlpoutputs=[512, 256, 128],
                 bottom_mlpoutputs=[1024, 1024, 512, 256, 1],
                 userInput=None):
        self.offset = offset
        self.input_seq_len = input_seq_len  #number of lookups per sample
        self.d_model = d_model  # Embedding size
        self.top_mlpoutputs = top_mlpoutputs  #list of top mlps
        self.bottom_mlpoutputs = bottom_mlpoutputs
        self.denseinputfeatures = denseinputfeatures
        self.vocab_size = vocab_size  # Size of vocabulary in token embedding
        self.global_batch = global_batch
        self.local_batch_size = local_batch_size
        self.no_embedding_local = no_embedding_local
        self.no_embedding_total = no_embedding_total
        self.factor = self.global_batch / self.local_batch_size
        super().__init__(name, verbose, userInput=userInput)

    def create(self):

        self.addInputTensor(Tensor.from_dims("dense_input", (self.batch, self.denseinputfeatures, 1, 1)))
        self.addInputTensor(Tensor.from_dims(
            "input_embedded_local", (self.batch * self.factor, self.input_seq_len, self.no_embedding_local, 1)),
                            override_batch=False)
        self.addInputTensor(
            Tensor.from_dims("input_embedded_comm",
                             (self.batch, 1, self.no_embedding_total - self.no_embedding_local, self.d_model)))
        self.addInputTensor(Tensor.from_dims("sample_input2", (self.batch, self.batch, 1, 1)))
        dense_input = self.input_tensors[0]
        input_embed_local = self.input_tensors[1]
        input_embed_comm = self.input_tensors[2]
        sample_second_input = self.input_tensors[3]
        embed_local_out = self.add(
            layer_factory.get_layer("Embed",
                                    "Embedding", [input_embed_local],
                                    num_output=self.d_model,
                                    input_dim=self.vocab_size))

        reduction_local_out = self.add(
            layer_factory.get_layer("Reduction", "reduction_local", input_tensors=[embed_local_out], axis=1))

        sampled_local = self.add(
            layer_factory.get_layer("GatherFromTensor",
                                    "sample_local",
                                    input_tensors=[reduction_local_out, sample_second_input]))
        concat_embed = self.add(
            layer_factory.get_layer("Concat", "Embed_Concat", input_tensors=[sampled_local, input_embed_comm], axis=2))

        mlp1_out = self.add(
            layer_factory.get_layer("Dense", "top_mlp1", dense_input, self.top_mlpoutputs[0], input_tensor_rank=2))
        relu1_out = self.add(layer_factory.get_layer("Relu", "top_relu1", mlp1_out))
        mlp2_out = self.add(
            layer_factory.get_layer("Dense", "top_mlp2", relu1_out, self.top_mlpoutputs[1], input_tensor_rank=2))
        relu2_out = self.add(layer_factory.get_layer("Relu", "top_relu2", mlp2_out))
        mlp3_out = self.add(
            layer_factory.get_layer("Dense", "top_mlp3", relu2_out, self.top_mlpoutputs[2], input_tensor_rank=2))
        relu3_out = self.add(layer_factory.get_layer("Relu", "top_relu3", mlp3_out))

        relu3_out_reshaped = self.add(
            layer_factory.get_layer("Reshape",
                                    "top_mlp_reshape",
                                    input_tensors=relu3_out,
                                    reshape_dim=[relu3_out.batch, relu3_out.width, relu3_out.height,
                                                 relu3_out.channel]))

        concat_before_batchmatmul = self.add(
            layer_factory.get_layer("Concat", "concat_before_batchmatmul", [relu3_out_reshaped, concat_embed], axis=2))
        batch_matmul_transpose_in = self.add(
            layer_factory.get_layer("Transpose",
                                    "transpose",
                                    input_tensors=concat_before_batchmatmul,
                                    perm=[0, 1, 3, 2]))
        batch_matmul_out = self.add(
            layer_factory.get_layer("MatMul", "batch_mat_mul", [concat_before_batchmatmul, batch_matmul_transpose_in]))

        offset_trilo = self.add(
            layer_factory.get_layer("TriangularIndices", "trilooffset", batch_matmul_out, self.offset))
        offset_output = self.add(layer_factory.get_layer("Select", "offset_output", [batch_matmul_out, offset_trilo]))
        concat_before_bottom_mlp = self.add(
            layer_factory.get_layer("Concat", "concat_before_bottom_mlp", [offset_output, relu3_out], axis=1))
        bottom_mlp1_out = self.add(
            layer_factory.get_layer("Dense",
                                    "bottom_mlp1",
                                    concat_before_bottom_mlp,
                                    self.bottom_mlpoutputs[0],
                                    input_tensor_rank=2))
        relu1_bottom_out = self.add(layer_factory.get_layer("Relu", "relu1_bottom_out", bottom_mlp1_out))
        bottom_mlp2_out = self.add(
            layer_factory.get_layer("Dense",
                                    "bottom_mlp2",
                                    relu1_bottom_out,
                                    self.bottom_mlpoutputs[1],
                                    input_tensor_rank=2))
        relu2_bottom_out = self.add(layer_factory.get_layer("Relu", "relu2_bottom_out", bottom_mlp2_out))
        bottom_mlp3_out = self.add(
            layer_factory.get_layer("Dense",
                                    "bottom_mlp3",
                                    relu2_bottom_out,
                                    self.bottom_mlpoutputs[2],
                                    input_tensor_rank=2))
        relu3_bottom_out = self.add(layer_factory.get_layer("Relu", "relu3_bottom_out", bottom_mlp3_out))
        bottom_mlp4_out = self.add(
            layer_factory.get_layer("Dense",
                                    "bottom_mlp4",
                                    relu3_bottom_out,
                                    self.bottom_mlpoutputs[3],
                                    input_tensor_rank=2))
        relu4_bottom_out = self.add(layer_factory.get_layer("Relu", "relu4_bottom_out", bottom_mlp4_out))
        bottom_mlp5_out = self.add(
            layer_factory.get_layer("Dense",
                                    "bottom_mlp5",
                                    relu4_bottom_out,
                                    self.bottom_mlpoutputs[4],
                                    input_tensor_rank=2))
        #relu5_bottom_out = self.add(layer_factory.get_layer("Relu", "relu5_bottom_out", bottom_mlp5_out))

        sigmoid_output = self.add(layer_factory.get_layer("Sigmoid", "sigmoid_final", bottom_mlp5_out))
        return sigmoid_output
