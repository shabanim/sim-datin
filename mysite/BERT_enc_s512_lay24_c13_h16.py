from networks.BERTforClassification import BERTforClassification


# Use case1: Email Filtering.
#   Once for sentiment, and a 2nd time for NER
#   25 emails.
#
class BERT_enc_s512_lay24_c13_h16(BERTforClassification):
    def __init__(self, name, verbose=False, userInput=None):
        input_seq_len = 512  # length of input sequence
        d_model = 768  # Model dim
        num_enc_layers = 24  # Num of encoder layers
        num_heads = 16  # Num of attention heads
        vocab_size = 30522  # Size of vocabulary in token embedding
        num_classes = 13  # Num of classes for classification

        super().__init__(name, input_seq_len, d_model, num_enc_layers, num_heads, vocab_size, num_classes, verbose,
                         userInput)
