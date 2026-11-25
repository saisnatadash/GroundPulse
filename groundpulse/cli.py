"""Command-line demo: python -m groundpulse.cli data/demo_scenario.json"""
import sys
from .scenario import load_engine


def main(argv):
    path = argv[1] if len(argv) > 1 else "data/demo_scenario.json"
    eng = load_engine(path)
    snap = eng.snapshot()
    print(f"Reports received: {snap['kpis']['reports']}")
    print(f"Forwards collapsed to one observation: {snap['kpis']['forwards_collapsed']}")
    print(f"Open incidents: {snap['kpis']['open_incidents']}  Contradicted: {snap['kpis']['contradicted']}")
    print()
    for inc in snap["incidents"]:
        print(f"INC-{inc['id']} [{inc['category']}] state={inc['state']} priority={inc['priority']}")
        print(f"   latest: {inc['text']}")
        print(f"   independent={inc['independent']} forwards={inc['forwards']} credibility={inc['credibility']}")
        if inc["conflict"]:
            print(f"   conflict: {inc['conflict']}")
        print(f"   reasons: {', '.join(inc['reasons'])}")
    print()
    for z in snap["zones"]:
        print(f"Zone {z['name']}: {z['status']}")
    print("\nNo dispatch action exists in this prototype. Resources move only on a human decision.")


if __name__ == "__main__":
    main(sys.argv)
