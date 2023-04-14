import time
import json
from lursoft_lv import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()
    final_data = a.Execute(
        "aHR0cHM6Ly9jb21wYW55Lmx1cnNvZnQubHYvZW4vY2l0YWRlbGUtYmFua2EvNDAxMDMzMDM1NTk=",
        "graph:shareholders",
        "",
        "",
    )

    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
