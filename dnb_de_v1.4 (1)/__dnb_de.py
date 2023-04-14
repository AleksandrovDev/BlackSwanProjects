from dnb_de import *
import json

if __name__ == "__main__":
    C = Handler()

    cont = C.Execute(
        "aHR0cHM6Ly93d3cuZG5iLmNvbS9kZS1kZS9maXJtZW5wcm9maWwvMzE1NTM3OTQ0L2NvbW1lcnpiYW5rX2FrdGllbmdlc2VsbHNjaGFmdA==",
        "documents",
        "",
        "",
    )

    try:
        print(
            json.dumps(cont, ensure_ascii=False, indent=2).encode("utf8").decode("utf8")
        )
    except Exception as e:
        print(cont)
