# this tool is used to generate a list of input files of the folder
import sys
import os

def generate_list(dir_path, rep_base=False):
    """
    list the folders and return a list 
    """
    dir_list = [os.path.join(dir_path, i) for i in os.listdir(dir_path)]
    # all the package should be folders
    res = []
    for d in dir_list:
        if os.path.isdir(d):
            if rep_base:
                base_name = os.path.basename(d)
                res.append(os.path.join(os.path.abspath(d), base_name))
            else:
                res.append(os.path.abspath(d))
    return res

input_dir = sys.argv[1]
rep_base = False
if len(sys.argv) > 2:
    rep_base = True
generated_list = generate_list(input_dir, rep_base)
with open("result.list", 'w') as fp:
    fp.write('\n'.join(generated_list))
