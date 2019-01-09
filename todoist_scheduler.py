import os
import _pickle as pickle
import application
from globs import *

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

    for k, v in a.store.d.items():
        print('==============================')
        print("now: {}".format(k))
        print("total_blocks: {}".format(v['total_blocks']))
        print("break_blocks: {}".format(v['break_blocks']))
        print("percent: {}".format(v['percent']))
        print("efficiency: {}".format(v['efficiency']))
        print("total_time: {}".format(v['total_time']))
        print("break_time: {}".format(v['break_time']))
        print("productive_time: {}".format(v['productive_time']))

