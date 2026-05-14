import json
import paths


def _display(rubric: dict):
    dims = rubric["dimensions"]
    total = sum(d["weight"] for d in dims)
    print("\n" + "=" * 68)
    print("  RUBRIC DRAFT")
    print("=" * 68)
    for i, d in enumerate(dims, 1):
        print(f"\n  [{i}] {d['name']}  (weight: {d['weight']})")
        print(f"      ID: {d['dimension_id']}")
        print(f"      Score 10: {d['description_of_10']}")
    print(f"\n  Total weight: {total:.3f}")
    print("=" * 68)


def run() -> str:
    rubric = json.loads(paths.RUBRIC_DRAFT.read_text())

    while True:
        _display(rubric)
        print("\n  [A] Approve")
        print("  [E] Edit a dimension")
        print("  [R] Reject and regenerate")
        choice = input("\n  Choice: ").strip().upper()

        if choice == "A":
            paths.APPROVED_RUBRIC.parent.mkdir(parents=True, exist_ok=True)
            paths.APPROVED_RUBRIC.write_text(json.dumps(rubric, indent=2))
            print("  Approved rubric saved.")
            return "approved"

        elif choice == "E":
            dims = rubric["dimensions"]
            try:
                idx = int(input(f"  Dimension number (1-{len(dims)}): ").strip()) - 1
                if not (0 <= idx < len(dims)):
                    raise ValueError
            except ValueError:
                print(f"  Invalid. Enter 1-{len(dims)}.")
                continue

            dim = dims[idx]
            print(f"\n  Editing: {dim['name']}")
            print("  [1] name")
            print("  [2] description_of_10")
            print("  [3] weight")
            field = input("  Field: ").strip()

            if field == "1":
                dim["name"] = input("  New name: ").strip()
            elif field == "2":
                dim["description_of_10"] = input("  New description_of_10: ").strip()
            elif field == "3":
                try:
                    dim["weight"] = float(input("  New weight: ").strip())
                    total = sum(d["weight"] for d in dims)
                    if abs(total - 1.0) > 0.001:
                        print(f"  Warning: weights now sum to {total:.3f} (must be 1.0 before approving)")
                except ValueError:
                    print("  Invalid weight.")
            else:
                print("  Invalid field choice.")

        elif choice == "R":
            print("  Rejecting — will regenerate.")
            return "rejected"

        else:
            print("  Enter A, E, or R.")
