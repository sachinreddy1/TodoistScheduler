import os
import _pickle as pickle
import application
from globs import *

if __name__ == "__main__":
    if not os.path.exists(pickle_path):
        a = application.Application()
        a.run()
        pickle.dump(a, open(pickle_path, "wb"))
    else:
        a = pickle.load(open(pickle_path, "rb"))
        a.run()
        pickle.dump(a, open(pickle_path, "wb"))
