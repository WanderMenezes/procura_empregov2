from pathlib import Path

base = Path(r'c:\xampp\htdocs\procura_empregov2\templates')
changes = [
    ('templates/profiles/wizard.html', [
        ('O progresso e guardado automaticamente enquanto preenches.', 'O progresso é guardado automaticamente enquanto preenches.'),
    ]),
    ('templates/dashboard/offline_registration_form_document.html', [
        ('<label for="endereco">Endereco</label>', '<label for="endereco">Endereço</label>'),
    ]),
    ('templates/core/help.html', [
        ('<li><strong>Endereco:</strong> São Tomé, São Tomé e Príncipe</li>', '<li><strong>Endereço:</strong> São Tomé, São Tomé e Príncipe</li>'),
    ]),
    ('templates/dashboard/offline_registrations.html', [
        ('formulário offline preenchivel', 'formulário offline preenchível'),
    ]),
    ('templates/profiles/assisted_register.html', [
        ('dados basicos de enquadramento do jovem.', 'dados básicos de enquadramento do jovem.'),
    ]),
    ('templates/companies/_search_results.html', [
        ('Localidade nao definida', 'Localidade não definida'),
    ]),
]
for rel_path, items in changes:
    path = base.parent / rel_path
    text = path.read_text(encoding='utf-8')
    updated = text
    for raw, fixed in items:
        updated = updated.replace(raw, fixed)
    if updated != text:
        path.write_text(updated, encoding='utf-8')
        print(rel_path)
