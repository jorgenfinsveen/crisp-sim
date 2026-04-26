#! /usr/bin/python3

import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--graphics",  required=False,  help="Comma-separated list of the names of the graphics apps to parse.")
parser.add_argument("--compute",  required=False,  help="Comma-separated list of the names of the compute apps to parse.")
parser.add_argument("--src_graphics",  required=True, help="Path to the source directory of the graphics traces.")
parser.add_argument("--src_compute",  required=True, help="Path to the source directory of the compute traces.")
parser.add_argument("--dest", required=False, help="Path to the destination directory.")
args = parser.parse_args()

trace_dir_graphics = args.src_graphics + "/"
trace_dir_compute = args.src_compute + "/"

if not args.graphics or args.graphics == "*": gs = os.listdir(trace_dir_graphics)
else: gs = args.graphics.split(",")

if not args.compute or args.compute == "*": cs = os.listdir(trace_dir_compute)
else: cs = args.compute.split(",")

# "ritnet", "hotlab",
css = []

vio = 1
all_name = "ALL"

# to clean up
for g in gs:
    for c in cs + css:
        if os.path.exists(trace_dir_graphics + g + "/" + c):
            os.system("rm -rf " + trace_dir_graphics + g + "/" + c)
    # rm all
    if os.path.exists(trace_dir_graphics + g + "/" + all_name):
        os.system("rm -rf " + trace_dir_graphics + g + "/" + all_name)

# exit()

for g in gs:
    if os.path.exists(trace_dir_graphics + g + "/" + all_name):
        print("skipping " + g + "/" + all_name)
    else:
        os.makedirs(trace_dir_graphics + g + "/" + all_name + "/traces", exist_ok=True)
        # copy over traces
        os.system("ln -s " + trace_dir_graphics+ g + "/NO_ARGS/traces/*.traceg " + trace_dir_graphics + g + "/" + all_name + "/traces/")
        # copy over kernelslist.g
        os.system("cp " + trace_dir_graphics + g + "/NO_ARGS/traces/kernelslist.g " + trace_dir_graphics + g + "/" + all_name + "/traces/")
    for c in cs + css:
        # check if dir exits
        if os.path.exists(trace_dir_graphics + g + "/" + c):
            print("skipping " + g + "/" + c)
        else:
            print("creating " + g + "/" + c)
            os.makedirs(trace_dir_graphics + g + "/" + c + "/traces", exist_ok=True)
            # copy over traces
            os.system("ln -s " + trace_dir_graphics + g + "/NO_ARGS/traces/*.traceg " + trace_dir_graphics + g + "/" + c + "/traces/")
            # copy over kernelslist.g
            os.system("cp " + trace_dir_graphics + g + "/NO_ARGS/traces/kernelslist.g " + trace_dir_graphics + g + "/" + c + "/traces/")

# write compute kernels to each cs kernelslist.g
    for c in cs:
        # get sub dir of c
        sub_dir = trace_dir_compute + c + "/" + os.listdir(trace_dir_compute + c + "/")[0]
        # read in file traceg

        kernelslist = open(trace_dir_graphics + g + "/" + c + "/traces/kernelslist.g", "a+")

        # add lines to kernelslist.g
        kernelslist.write("\n")
        kernelslist_c = open(sub_dir + "/traces/kernelslist.g", "r")
        for line in kernelslist_c:
            kernelslist.write(c + "-" + line)
        kernelslist_c.close()
        kernelslist.close()

# write compute kernels (up to n times) to all kernelslist.g
    for i in range(0,vio):
        for c in cs:
            sub_dir = trace_dir_compute + c + "/" + os.listdir(trace_dir_compute + c + "/")[0]
            kernelslist_all = open(trace_dir_graphics + g + "/" + all_name + "/traces/kernelslist.g", "a+")
            kernelslist_all.write("\n")
            kernelslist_c = open(sub_dir + "/traces/kernelslist.g", "r")
            for line in kernelslist_c:
                kernelslist_all.write(c + "-" + line)
            kernelslist_all.close()

# link the compute trace files
    for c in cs:
        sub_dir = trace_dir_compute + c + "/" + os.listdir(trace_dir_compute + c + "/")[0]
        # copy over files in sub_dir and rename
        for file in os.listdir(sub_dir + "/traces"):
            if file == "kernelslist.g" or file == "stats.csv":
                continue
            os.system("ln -s " + sub_dir + "/traces/" + file + " " + trace_dir_graphics + g + "/" + c + "/traces/" + c + "-" + file)
            os.system("ln -s " + sub_dir + "/traces/" + file + " " + trace_dir_graphics + g + "/" + all_name + "/" + "/traces/" + c + "-" + file)

# write compute kernels to each css kernelslist.g (not part of all)
    for c in css:
        # get sub dir of c
        sub_dir = trace_dir_compute + c + "/" + os.listdir(trace_dir_compute + c + "/")[0]
        # read in file traceg

        kernelslist = open(trace_dir_compute + g + "/" + c + "/traces/kernelslist.g", "a+")

        # add lines to kernelslist.g
        kernelslist.write("\n")
        kernelslist_c = open(sub_dir + "/traces/kernelslist.g", "r")
        for line in kernelslist_c:
            kernelslist.write(c + "-" + line)
        kernelslist_c.close()
        kernelslist.close()
        for file in os.listdir(sub_dir + "/traces"):
            if file == "kernelslist.g" or file == "stats.csv":
                continue
            os.system("ln -s " + sub_dir + "/traces/" + file + " " + trace_dir_graphics + g + "/" + c + "/traces/" + c + "-" + file)
            # os.system("ln -s " + sub_dir + "/traces/" + file + " " + trace_dir + g + "/" + all_name + "/" + "/traces/" + c + "-" + file)
