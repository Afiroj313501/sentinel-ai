import pickle
import subprocess

PASSWORD = "hunter2"


def run(command):
    subprocess.call(command, shell=True)


def calculate(expression):
    return eval(expression)


def load(blob):
    return pickle.loads(blob)
