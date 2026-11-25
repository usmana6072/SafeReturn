import os, re, sys
root = r'e:\\Projects\\SafeReturn\\backend\\app\\api\\v1'
# List of tuples (filename, function name)
missing = [
    ('account_lifecycle.py', 'suspend'),
    ('account_lifecycle.py', 'restore'),
    ('account_lifecycle.py', 'recovery'),
    ('cancellations.py', 'reconcile'),
    ('cancellations.py', 'decide'),
    ('cancellations.py', 'release'),
    ('catalog_templates.py', 'choices'),
    ('dashboard.py', 'summary'),
    ('dashboard.py', 'trends'),
    ('finance_reconciliation.py', 'reconciliation'),
    ('finance_reconciliation.py', 'counts'),
    ('financial_disputes.py', 'review'),
    ('financial_disputes.py', 'decide'),
    ('fulfillment.py', 'create_shipment'),
    ('fulfillment.py', 'create_shipment_from_order'),
    ('fulfillment.py', 'update_shipment'),
    ('independent_finance.py', 'reconciliation'),
    ('independent_finance.py', 'review'),
    ('independent_finance.py', 'retry'),
    ('printing.py', 'record_job_qa'),
    ('printing.py', 'physical_qa'),
    ('printing.py', 'submit_physical_qa'),
    ('print_queries.py', 'counts'),
    ('print_queries.py', 'jobs'),
    ('print_templates.py', 'listing'),
    ('print_templates.py', 'create'),
    ('print_templates.py', 'detail'),
    ('print_templates.py', 'revision'),
    ('print_templates.py', 'edit'),
    ('print_templates.py', 'preview'),
    ('print_templates.py', 'submit'),
    ('print_templates.py', 'publish'),
    ('print_templates.py', 'bind'),
    ('print_templates.py', 'bindings'),
    ('print_templates.py', 'retire'),
    ('print_templates.py', 'qa_status'),
    ('print_templates.py', 'qa_decision'),
    ('staff_directory.py', 'users'),
    ('staff_directory.py', 'total'),
    ('staff_directory.py', 'detail'),
    ('support_metadata.py', 'cases'),
    ('support_metadata.py', 'case'),
    ('support_metadata.py', 'events'),
    ('typed_inventory.py', 'batches'),
    ('typed_inventory.py', 'batch_detail'),
    ('typed_inventory.py', 'summary'),
    ('typed_inventory.py', 'codes'),
    ('typed_inventory.py', 'code_detail'),
]
# Map file to set of functions
file_to_funcs = {}
for fname, func in missing:
    file_to_funcs.setdefault(fname, set()).add(func)

for fname, funcs in file_to_funcs.items():
    path = os.path.join(root, fname)
    with open(path, 'r', encoding='utf8') as f:
        lines = f.readlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        stripped = line.lstrip()
        for func in list(funcs):
            if stripped.startswith(f'def {func}('):
                # Determine indentation (same as line)
                indent = re.match(r'^(\s*)', line).group(1) + '    '
                # Insert require_staff after def line
                new_lines.append(f"{indent}require_staff(context, \"operations\")\n")
                funcs.remove(func)
                break
        i += 1
    # Write back
    with open(path, 'w', encoding='utf8') as f:
        f.writelines(new_lines)
print('Guards inserted')
