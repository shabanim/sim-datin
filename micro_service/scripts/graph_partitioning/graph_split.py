import csv

with open("C:/Users/aneriach/OneDrive - Intel Corporation/Desktop/New folder/TransformerLanguageModel_17B.py_layer_stat.csv") as fin1:
    layer_stat = [row for row in csv.DictReader(fin1)]

layers_list=[]
for layers in layer_stat:
    if layers['Pass']=='fwd':
        temp={"Layer Idx":layers['Layer Idx'],
              "Layer Name": layers['Layer Name'],
              "Layer Type":layers['Layer Type'],
              "Input Tensor dims":layers['Input Tensor dims'],
              "Input Tensor Size (Ki)":layers['Input Tensor Size (Ki)'],
              "Output Tensor Dims":layers['Output Tensor Dims'],
              "Output Tensor Size (Ki)":layers['Output Tensor Size (Ki)'],
              "Weight Size (Ki)":layers['Weight Size (Ki)']}
        #print(temp)
        layers_list.append(temp)

#print(layers_list)

output_list=[]
for i in range(len(layers_list)):
    #print(layers_list[i]['Layer Idx'])
    layer_id= layers_list[i]['Layer Idx']
    #print(layer_id)
    output_name = layers_list[i]['Output Tensor Dims']
    #print(output_name)
    for j in range(len(layers_list)):
        layers_list[j]['Input Tensor dims'] = layers_list[j]['Input Tensor dims'].replace(output_name, layer_id)
    layers_list[i]['Output Tensor Dims']=layer_id
    output_list.append(layer_id)
print(output_list)
for i in range(len(layers_list)):
    input_name = layers_list[i]['Input Tensor dims'].split(',')
    for item in input_name:
        if item not in output_list:
            layers_list[i]['Input Tensor dims'] = layers_list[i]['Input Tensor dims'].replace(item, '-1')


csv_file = "Names.csv"
csv_columns = ['Layer Idx','Layer Name','Layer Type','Input Tensor dims','Input Tensor Size (Ki)','Output Tensor Dims',
               'Output Tensor Size (Ki)','Weight Size (Ki)']
try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in layers_list:
            writer.writerow(data)
except IOError:
    print("I/O error")


#Till Here its loading and parsing the graph according to our req.


#model_split_layers = ['Dense']
last_model_split_layer= 0
counter=0
for i in range(len(layers_list)):
    if layers_list[i]['Layer Type']== 'Dense':
        layers_list[i]['recent_dense_layer_id'] = str(i)
    elif layers_list[i]['Layer Type']== 'Add':
        layers_list[i]['recent_dense_layer_id'] = 'nan'
    else:
        #input_id =((max(list(map(int, layers_list[i]['Input Tensor dims'].split(','))) )))
        input_id = list(map(int, layers_list[i]['Input Tensor dims'].split(',')))
        if input_id == [-1]:
            layers_list[i]['recent_dense_layer_id'] = 'nan'
        else:
            #layers_list[i]['recent_dense_layer_id'] =layers_list[input_id]['recent_dense_layer_id']
            dummy_list =[]
            dummy_str=""
            #print('-----')
            for values in input_id:
                  dummy_list.append(layers_list[values]['recent_dense_layer_id'])   #????
            for dum in dummy_list:
                dummy_str = dummy_str+str(dum)+","
            layers_list[i]['recent_dense_layer_id'] = dummy_str[:-1]

    #print(type(layers_list[i]['recent_dense_layer_id']))


csv_file = "Names.csv"
csv_columns = ['Layer Idx','Layer Name','Layer Type','Input Tensor dims','Input Tensor Size (Ki)','Output Tensor Dims',
               'Output Tensor Size (Ki)','Weight Size (Ki)','recent_dense_layer_id']
try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in layers_list:
            writer.writerow(data)
except IOError:
    print("I/O error")

last_model_split_layer= 0
counter=0
for i in range(len(layers_list)):
    if layers_list[i]['Layer Type']== 'Dense':
        #input_id = ((max(list(map(int, layers_list[i]['Input Tensor dims'].split(','))))))
        input_id = list(map(int, layers_list[i]['Input Tensor dims'].split(',')))
        print(input_id)
        for values in input_id:
            previous_dense_layer_id = layers_list[values]['recent_dense_layer_id']
            print((previous_dense_layer_id))
            if previous_dense_layer_id=='nan':
                layers_list[i]['verticle_split'] = '1'
                layers_list[i]['Horizontal_split'] = '0'
                layers_list[i]['comms_type'] = 'allgather'

            else:
                previous_dense_layer_id = list(map(int, layers_list[values]['recent_dense_layer_id'].split(',')))
                print((previous_dense_layer_id))
                counter1 = 0
                counter2 = 0
                for items in previous_dense_layer_id:
                    print(items)
                    items = int(items)
                    if ((layers_list[items]['verticle_split'] == '1') and (
                            layers_list[items]['Horizontal_split'] == '0')):
                        counter1+=1
                    elif ((layers_list[items]['verticle_split'] == '0') and (
                            layers_list[items]['Horizontal_split'] == '1')):
                        counter1 += 1
                if (counter1 == len(previous_dense_layer_id)) or (counter1 == len(previous_dense_layer_id)):  #???
                    print("Done")
                    items=max(list(map(int, layers_list[values]['recent_dense_layer_id'].split(','))))
                    if ((layers_list[items]['verticle_split'] == '1') and (layers_list[items]['Horizontal_split'] == '0')):
                        layers_list[i]['verticle_split'] = '0'
                        layers_list[i]['Horizontal_split'] = '1'
                        layers_list[i]['comms_type'] = 'allreduce'
                        for j in previous_dense_layer_id:
                            print(j)
                            j = int(j)
                            layers_list[j]['comms_type'] = '0'
                    elif ((layers_list[previous_dense_layer_id]['verticle_split'] == '0') and (layers_list[previous_dense_layer_id]['Horizontal_split'] == '1')):
                        layers_list[i]['verticle_split'] = '1'
                        layers_list[i]['Horizontal_split'] = '0'
                        layers_list[i]['comms_type'] = 'allgather'
                else:
                    layers_list[i]['verticle_split'] = '1'
                    layers_list[i]['Horizontal_split'] = '0'
                    layers_list[i]['comms_type'] = 'allgather'
    else:
        layers_list[i]['verticle_split'] = '0'
        layers_list[i]['Horizontal_split'] = '0'
        layers_list[i]['comms_type'] = '0'

csv_file = "Names.csv"
csv_columns = ['Layer Idx', 'Layer Name', 'Layer Type', 'Input Tensor dims', 'Input Tensor Size (Ki)',
               'Output Tensor Dims',
               'Output Tensor Size (Ki)', 'Weight Size (Ki)', 'recent_dense_layer_id','verticle_split','Horizontal_split',
               'comms_type']
try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in layers_list:
            writer.writerow(data)
except IOError:
    print("I/O error")




