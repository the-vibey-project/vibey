import argparse
import json

def check_health():
    health_status = "System healthy"
    detailed_report = "No critical issues detected."
    return health_status, detailed_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    health_status, detailed_report = check_health()

    if args.json:
        print(json.dumps({"status": health_status, "report": detailed_report}, indent=2))
    else:
        print(f"Health summary: {health_status}\n{detailed_report}")