import pickle
from matplotlib import pyplot as plt
from datetime import datetime

def get_timestamps(filename):
    with open(filename+".out", 'r') as F:
        lines = F.readlines()
    jobstart = [x for x in lines if "jobstart" in x]
    if len(jobstart)==1:
        jobstart = jobstart[0]
        jobstart = datetime.strptime(jobstart, "jobstart %a %d %b %Y %I:%M:%S %p %Z\n")
        print(jobstart)
        jobstart = jobstart.timestamp()
    else:
        jobstart = None

    jobend = [x for x in lines if "jobend" in x]
    if len(jobend)==1:
        jobend = jobend[0]
        jobend = datetime.strptime(jobend, "jobend %a %d %b %Y %I:%M:%S %p %Z\n")
        jobend = jobend.timestamp()
    else:
        jobend = None

    with open(filename+".err", 'r') as F:
        lines = F.readlines()
    print(lines[0])

    if jobstart:
        t_zero = jobstart
    else:
        t_zero = lines[0].split(" | ")[1]
        t_zero = datetime.strptime(t_zero, "%Y-%m-%d %H:%M:%S,%f")
        t_zero = t_zero.timestamp()

    logger = {}
    for l in lines:
        try:
            rank, time, line = l.split(" | ")
        except:
            print(f"Couldn't read '{l}'")
            continue
        line = line.rstrip()
        time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S,%f")
        time = time.timestamp() - t_zero
        if line not in logger:
            logger[line] = []
        logger[line].append(time)

    items = {x:len(logger[x]) for x in logger.keys()}

    interesting = [ 'EVENT: read input pickle',
                    'EVENT: BEGIN prep dataframe',
                    'EVENT: DONE prep dataframe',
                    'EVENT: begin loading inputs',
                    'EVENT: BEGIN loading experiment list',
                    'EVENT: DONE loading experiment list',
                    'EVENT: LOADING ROI DATA',
                    'EVENT: DONE LOADING ROI',
                    'EVENT: Gathering global HKL information',
                    'EVENT: FINISHED gather global HKL information',
                    'EVENT: launch refiner',
                    'DONE WITH FUNC GRAD',
                    '_launcher done running optimization']
    interesting = [s for s in interesting if s in logger]

    times = {}
    for l in interesting:
        timelist = []
        for t in logger[l]:
            timelist.append(t)
        times[l] = timelist

    return times


if __name__=="__main__":
    import sys, os
    filename = sys.argv[1]
    timestamps = get_timestamps(filename)
    if not os.path.exists("timestamps"):
        os.mkdir("timestamps")
    with open(f"timestamps/{filename}.pkl", 'wb') as F:
        pickle.dump(timestamps, F)
