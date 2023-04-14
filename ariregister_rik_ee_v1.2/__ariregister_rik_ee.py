import time
import json
from ariregister_rik_ee import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()

    final_data = a.Execute("AAA Patendi", "", "", "")
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
