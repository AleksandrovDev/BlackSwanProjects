import time
import json
from nse_or_jp import *

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()

    final_data = a.Execute(
        "eyduYW1lJzogJ1RoZSBPZ2FraSBLeW9yaXRzdSBCYW5rLEx0ZC4nLCAnaW5kJzogJ0JhbmtzJywgJ3VybCc6ICcnLCAnaWRlbnQnOiAnODM2MTAnLCAnbGluayc6ICdodHRwczovL3d3dy5uc2Uub3IuanAvYXBpL3N0b2NrL3NlYXJjaC5qc29uP3N0b2NrQ29kZT0mc3RvY2tOYW1lX2U9QmFuayZsaXN0ZWRTaW5nbGU9bnVsbCZpbmR1c3RyeUNvZGU9Jmxpc3RlZENsb3NlPSZ0cmFkaW5nVW5pdD0mZGlzcFR5cGU9c3RvY2tDb2RlJmRpc3BPcmRlcj1BU0MmZGlzcENvdW50PTEwJmRpc3BQYWdlPTEnfQ==",
        "overview",
        "",
        "",
    )

    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
