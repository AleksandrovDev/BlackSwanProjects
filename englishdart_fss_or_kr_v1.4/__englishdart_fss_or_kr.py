import time
import json
from englishdart_fss_or_kr import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()

    final_data = a.Execute(
        "MDA1OTMwPz1TQU1TVU5HIEVMRUNUUk9OSUNT", "Financial_Information", "", ""
    )
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
