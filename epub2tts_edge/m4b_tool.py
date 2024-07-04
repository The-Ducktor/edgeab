import subprocess

def merge(in_dir, out_file, cover="/Users/jacks/Documents/Git/devstuff/smartphone.jpg"):
    command = ["m4b-tool", "merge", in_dir, "--output-file", out_file,"--cover",cover,"--debug","--jobs=4"]

    subprocess.run(command)