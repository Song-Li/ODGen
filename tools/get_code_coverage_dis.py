# get the distribution of code coverage
def put_into_bins(cc_list):
    res = [0] * 10
    for cc in cc_list:
        idx = int((cc - 0.001) * 10)
        res[idx] += 1
    
    for idx in range(len(res)):
        res[idx] /= len(cc_list)
    return res

with open("../logs/stat.log", 'r') as fp:
    cc_list = [float(n) for n in fp.readlines()]

    res = put_into_bins(cc_list)
    for idx in range(len(res)):
        print(f"{idx * 10} to {idx * 10 + 10}: {res[idx]}")
