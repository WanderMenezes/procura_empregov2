from pathlib import Path

base = Path(r'c:\xampp\htdocs\procura_empregov2\templates')
replacements = [
    ('grid-templat\u00e9-columns', 'grid-template-columns'),
    ('translat\u00e9X', 'translateX'),
    ('translat\u00e9Y', 'translateY'),
    ('text\u00e1rea', 'textarea'),
    ('p\u00e1gination', 'pagination'),
    ('candidat\u00e9', 'candidate'),
    ('help-v\u00eddeo', 'help-video'),
    ('wizard-file-stat\u00e9', 'wizard-file-state'),
    ('t\u00e9cnico-dashboard', 'tecnico-dashboard'),
    ('n\u00famero_vagas', 'numero_vagas'),
]
changed = []
for path in sorted(base.rglob('*.html')):
    text = path.read_text(encoding='utf-8')
    updated = text
    for raw, fixed in replacements:
        updated = updated.replace(raw, fixed)
    if updated != text:
        path.write_text(updated, encoding='utf-8')
        changed.append(str(path.relative_to(base)))
print('\n'.join(changed))
print(f'TOTAL={len(changed)}')
