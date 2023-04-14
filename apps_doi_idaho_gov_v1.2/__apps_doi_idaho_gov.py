import time
import json
from apps_doi_idaho_gov import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()
    final_data = a.Execute(
        "aHR0cHM6Ly9hcHBzLmRvaS5pZGFoby5nb3YvbWFpbi9QdWJsaWNGb3Jtcy9MaWNlbnNlU2VhcmNoRGV0YWlscz9pZD0xNTI0NTcmbGljPTAmdHlwZT0z",
        "officership",
        "",
        "",
    )
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
