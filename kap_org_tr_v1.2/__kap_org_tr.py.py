import time
import json
from kap_org_tr import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()

    final_data = a.Execute(
        "aHR0cHM6Ly93d3cua2FwLm9yZy50ci9lbi9zaXJrZXQtYmlsZ2lsZXJpL296ZXQvMTMwMy1hMS1jYXBpdGFsLXlhdGlyaW0tbWVua3VsLWRlZ2VybGVyLWEtcz89SW52ZXN0bWVudCBGaXJtcw==",
        "graph:shareholders",
        "",
        "",
    )
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
