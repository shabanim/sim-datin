import pandas as pd
import sys

def extract_info_table(url):
    dfs = pd.read_html(url)
    temp_dict = dfs[2].to_dict()

    info_dict = {}
    for idx,key in enumerate(temp_dict['Metric']):
        info_dict[temp_dict['Metric'][key]] = temp_dict['Value'][idx]

    print(info_dict)
    pass

if __name__ == "__main__":
    res = extract_info_table(sys.argv[1])
    import gc
    gc.collect()  # need this to terminate streams / threads that might be cleaned by __del__
    sys.exit(res)