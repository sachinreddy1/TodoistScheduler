import os
import application
from globs import *
import sys
if sys.version_info[0] < 3:
    import pickle as pickle
else:
    import _pickle as pickle

if __name__ == "__main__":
    if not os.path.exists(pickle_path):
        a = application.Application()
        a.run()
        pickle.dump(a, open(pickle_path, "wb"))
        pickle.dump(a.store.d, open(pickle_data_path, "wb"))
    else:
        a = pickle.load(open(pickle_path, "rb"))
        a.run()
        pickle.dump(a, open(pickle_path, "wb"))
        pickle.dump(a.store.d, open(pickle_data_path, "wb"))

