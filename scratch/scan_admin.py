import os, re, sys
root = r'e:\\Projects\\SafeReturn\\backend\\app\\api\\v1'
missing = []
for dirpath, _, files in os.walk(root):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(dirpath, f)
            with open(path, encoding='utf8') as fh:
                content = fh.read()
            # Find admin route decorators
            for match in re.finditer(r'@router\.(get|post|patch|delete)\s*\([^\)]*"(/admin/[^\"]*)"[^\)]*\)', content, re.DOTALL):
                # locate function definition after decorator
                after = content[match.end():]
                func_match = re.search(r'def\s+(\w+)\s*\(', after)
                if not func_match:
                    continue
                func_name = func_match.group(1)
                # extract function body up to next def or end
                start_idx = match.end() + func_match.start()
                body = content[start_idx:]
                # stop at next def
                next_def = re.search(r'\ndef\s+\w+\s*\(', body)
                if next_def:
                    body = body[:next_def.start()]
                if 'require_staff' not in body:
                    missing.append((path, func_name))
print('Missing require_staff in %d functions' % len(missing))
for p, fn in missing:
    print(p, fn)
