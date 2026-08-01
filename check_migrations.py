from pathlib import Path
import ast

versions = sorted(Path("migrations/versions").glob("*.py"))
revisions = {}
for path in versions:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = {node.targets[0].id: node.value.value for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"revision", "down_revision"} and isinstance(node.value, ast.Constant)}
    revisions[values["revision"]] = (values.get("down_revision"), path.name)
heads = {revision for revision in revisions} - {parent for parent, _ in revisions.values() if parent}
if len(heads) != 1:
    raise SystemExit(f"Expected one migration head, found: {heads}")
print(f"Migration chain OK: {next(iter(heads))}")
