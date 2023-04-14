from societe_com import *
import time
import json

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()
    final_data = a.Execute(
        "aHR0cHM6Ly93d3cuc29jaWV0ZS5jb20vc29jaWV0ZS9haXJidXMtMzgzNDc0ODE0Lmh0bWw=",
        "Financial_Information",
        "",
        "",
    )
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
