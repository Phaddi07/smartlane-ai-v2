import json
from pathlib import Path

schema_dir = Path("schemas")

for path in sorted(schema_dir.glob("*.schema.json")):
    schema = json.loads(path.read_text())

    print(f"\n{'=' * 70}")
    print(path.name)
    print(f"{'=' * 70}")

    for name, prop in schema.get("properties", {}).items():
        print(f"\n{name}:")
        print(f"  type: {prop.get('type')}")

        if "enum" in prop:
            print(f"  enum: {prop['enum']}")

        if "items" in prop:
            print(f"  items: {prop['items']}")

        if "properties" in prop:
            print("  nested properties:")
            for nested, nested_prop in prop["properties"].items():
                print(f"    {nested}: {nested_prop.get('type')}")
                if "enum" in nested_prop:
                    print(f"      enum: {nested_prop['enum']}")

    print(f"\nrequired: {schema.get('required', [])}")
