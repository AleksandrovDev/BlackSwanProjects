import time
import json
from kompass_com import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()

    final_data = a.Execute(
        "aHR0cHM6Ly93d3cua29tcGFzcy5jb20vZW4vYy9ieWJsb3MtYmFuay1zYWwvbGIwMDAxMDgv",
        "Financial_Information",
        "",
        "",
    )

    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
