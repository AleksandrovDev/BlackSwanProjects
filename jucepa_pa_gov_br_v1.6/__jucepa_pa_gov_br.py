from jucepa_pa_gov_br import *
import time
import json

if __name__ == "__main__":
    start_time = time.time()

    a = Handler()
    final_data = a.Execute(
        "eyJCQU5DTyBETyBFU1RBRE8gRE8gUEFSXHUwMGMxIFMuQS4iOiB7ImJzdDpidXNpbmVzc0NsYXNzaWZpZXIiOiBbeyJjb2RlIjogIjY0MjIxMDAiLCAiZGVzY3JpcHRpb24iOiAiQkFOQ09TIE1cdTAwZGFMVElQTE9TLCBDT00gQ0FSVEVJUkEgQ09NRVJDSUFMIiwgImxhYmVsIjogIiJ9LCB7ImNvZGUiOiAiNjQyMzkwMCIsICJkZXNjcmlwdGlvbiI6ICJDQUlYQVMgRUNPTlx1MDBkNE1JQ0FTIiwgImxhYmVsIjogIiJ9XSwgIm1kYWFzOlJlZ2lzdGVyZWRBZGRyZXNzIjogeyJjaXR5IjogIkNPTkNFSVx1MDBjN1x1MDBjM08gRE8gQVJBR1VBSUEiLCAiZnVsbEFkZHJlc3MiOiAiQVZFTklEQSBJTlRFTkRFTlRFIE5PUkJFUlRPIExJTUEsIEMgIEVOVFJPLCBDT05DRUlcdTAwYzdcdTAwYzNPIERPIEFSQUdVQUlBIn0sICJpZGVudGlmaWVycyI6IHsidmF0X3RheF9udW1iZXIiOiAiMDQuOTEzLjcxMS8wMDAxLTA4IiwgIm90aGVyX2NvbXBhbnlfaWRfbnVtYmVyIjogIjE1LTMtMDAwMDAxMS00In19fQ==",
        "branches",
        "",
        "",
    )
    print(json.dumps(final_data, indent=4))

    elapsed_time = time.time() - start_time
    print(
        "\nTask completed - Elapsed time: " + str(round(elapsed_time, 2)) + " seconds"
    )
