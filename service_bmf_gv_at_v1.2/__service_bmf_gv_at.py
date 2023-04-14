import time
import json
from service_bmf_gv_at import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()

    final_data = a.Execute("D\\xd6NMEZ Mehmet", "", "", "")
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
