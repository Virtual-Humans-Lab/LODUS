import os
import sys



d = sys.argv[1]

# pairs = zip(sys.argv[2::2], sys.argv[3::2])

# for pair in pairs:
#     print(pair)


# # source = sys.argv[2]
# # target = sys.argv[3]


for f_name in os.listdir(d):


    
    f_path = d + '\\' + f_name
    #print(f_path, end='\r')
    print(f_path)


    with open(f_path, 'r', encoding='utf-8') as f:
        text = f.read()

        text = text.replace("Mont\"Serrat", "Mont\'Serrat")
        text = text.replace("Passo D\"Areia", "Passo D\'Areia")
        
        
    with open(f_path, 'w', encoding='utf-8') as fw:
        fw.write(text)

