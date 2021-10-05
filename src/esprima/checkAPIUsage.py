def res_file_analyze():
    """
    read a file and analyze the frequency
    """
    f = open('./out.dat', 'r')
    freq = {}
    for line in f.readlines():
        line = line.strip()
        if line in freq:
            freq[line] += 1
        else:
            freq[line] = 1

    for key, value in sorted(freq.iteritems(), key=lambda (k,v): (-v,k)):
        print (key, value)

res_file_analyze()
