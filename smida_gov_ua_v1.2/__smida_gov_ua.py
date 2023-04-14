from smida_gov_ua import *
import time
import json

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()
    final_data = a.Execute(
        "aHR0cHM6Ly9zbWlkYS5nb3YudWEvZGIvcHJvZi8yMjkyNzA0NQ==",
        "graph:shareholders",
        "",
        "",
    )
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
