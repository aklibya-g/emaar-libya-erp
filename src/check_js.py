import re, sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'E:\EmarrCoSys\src\web\templates\marketing\work_order_form.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_script = False
depth = 0
for i, line in enumerate(lines):
    if '<script>' in line:
        in_script = True
        depth = 0
        continue
    if '</script>' in line:
        in_script = False
        continue
    if not in_script:
        continue
    # Skip pure Jinja lines
    stripped = line.strip()
    if stripped.startswith('{%') and stripped.endswith('%}'):
        continue
    # Replace Jinja expressions in-line
    clean = re.sub(r'\{\{.*?\}\}', '"x"', line)
    clean = re.sub(r'\{%.*?%\}', '', clean)
    old_depth = depth
    depth += clean.count('{') - clean.count('}')
    if old_depth >= 0 and depth < 0:
        print(f'NEGATIVE at HTML line {i+1}: depth went {old_depth}->{depth}')
        print(f'  Content: {line.rstrip()[:120]}')
        depth = 0
print(f'Final depth: {depth}')
