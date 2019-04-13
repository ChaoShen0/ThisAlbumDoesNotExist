import os

def makedirs(dir_path):
    try:
        os.makedirs(dir_path)
    except FileExistsError:
        pass
