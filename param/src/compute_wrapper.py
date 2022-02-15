import compute
from compute import *

compute = compute.Compute()
out = compute.qkv_projection()
print(out)
out = compute.self_Attn_InnerProd_and_Softmax()
print(out)
out = compute.self_Attn_scaled_weighting()
print(out)
out = compute.self_Attn_Concat_Merge_and_Layer_Norm()
print(out)
out = compute.Fused_Self_Atnn()
print(out)
out = compute.ff_1()
print(out)
out = compute.ff_2()
print(out)
out = compute.Projection()
print(out)




