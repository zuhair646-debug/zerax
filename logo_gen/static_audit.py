"""Static analysis of /kids HTML to find ALL duplicates, dead code, and broken bindings."""
import re
from collections import Counter, defaultdict

with open("/app/logo_gen/kids_current.html", "r", encoding="utf-8") as f:
    html = f.read()

print(f"Total HTML: {len(html)} bytes, {html.count(chr(10))} lines\n")

# 1. All <section id="..."> blocks
sections = re.findall(r'<section\s+id=["\']([^"\']+)["\']', html)
print(f"=== SECTIONS ({len(sections)}) ===")
for s in sections:
    print(f"  - {s}")

# 2. Duplicate function declarations
print(f"\n=== DUPLICATE FUNCTION DEFINITIONS ===")
fn_defs = defaultdict(list)
for m in re.finditer(r'(?:async\s+)?function\s+(\w+)\s*\(', html):
    fn_defs[m.group(1)].append(m.start())
for name, positions in sorted(fn_defs.items()):
    if len(positions) > 1:
        # Find which section each is in
        sec_for_pos = []
        for pos in positions:
            # Find nearest preceding <section id="">
            before = html[:pos]
            sec_match = list(re.finditer(r'<section\s+id=["\']([^"\']+)["\']', before))
            sec_id = sec_match[-1].group(1) if sec_match else "TOP-LEVEL"
            line = html[:pos].count("\n") + 1
            sec_for_pos.append(f"line {line} in <{sec_id}>")
        print(f"  {name}() defined {len(positions)}x:")
        for s in sec_for_pos:
            print(f"      {s}")

# 3. Duplicate element IDs
print(f"\n=== DUPLICATE ELEMENT IDs ===")
ids = re.findall(r'id=["\']([a-zA-Z][\w-]*)["\']', html)
id_counts = Counter(ids)
for eid, cnt in sorted(id_counts.items()):
    if cnt > 1:
        print(f"  #{eid}: {cnt}x")

# 4. Buttons without matching event listener
print(f"\n=== BUTTONS BY ID ===")
button_ids = re.findall(r'<button[^>]*id=["\']([^"\']+)["\']', html)
for bid in button_ids:
    # Check if there's an addEventListener or .onclick binding
    has_listener = bool(re.search(
        r'(getElementById\([\'"]' + re.escape(bid) + r'[\'"]\)\s*[?.][^;]*(?:addEventListener|onclick)|'
        r'\$\([\'"]#' + re.escape(bid) + r'[\'"]\)|'
        r'querySelector\([\'"]#' + re.escape(bid) + r'[\'"]\)\s*[?.][^;]*(?:addEventListener|onclick))',
        html
    ))
    onclick_attr = bool(re.search(r'<button[^>]*id=["\']' + re.escape(bid) + r'["\'][^>]*onclick', html))
    print(f"  #{bid:30} listener={has_listener}  onclick-attr={onclick_attr}")

print(f"\n=== TOTAL BUTTONS: {len(button_ids)} ===")
