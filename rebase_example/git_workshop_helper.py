import subprocess

def call(call):
    retval = subprocess.check_output(call.split()).decode('utf-8').split('\n') 
    retval.remove('')
    return retval
