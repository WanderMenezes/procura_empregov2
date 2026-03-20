from pathlib import Path

base = Path(r'c:\xampp\htdocs\procura_empregov2\templates')
replacements = [
    ('Nao informado', 'Não informado'),
    ('Nao informada', 'Não informada'),
    ('Nao definido', 'Não definido'),
    ('Nao definida', 'Não definida'),
    ('Nao definidos', 'Não definidos'),
    ('ainda nao definido', 'ainda não definido'),
    ('Distrito nao definido', 'Distrito não definido'),
    ('Instituicao nao informada', 'Instituição não informada'),
    ('Entidade nao informada', 'Entidade não informada'),
    ('A empresa ainda não públicou vagas.', 'A empresa ainda não publicou vagas.'),
    ('Dados pessoais basicos', 'Dados pessoais básicos'),
    ('botoes do formulario', 'botões do formulário'),
    ('dados base pedidos pelo formulario', 'dados base pedidos pelo formulário'),
    ('Gerar formulario preenchivel', 'Gerar formulário preenchível'),
    ('O formulario inclui', 'O formulário inclui'),
    ('JSON gerado pelo formulario', 'JSON gerado pelo formulário'),
    ('Distrito, endereco e logo ajudam', 'Distrito, endereço e logo ajudam'),
    ('Distrito e endereco ajudam', 'Distrito e endereço ajudam'),
    ('Completar contacto, endereco e descrição', 'Completar contacto, endereço e descrição'),
    ('contacto e endereco para criar', 'contacto e endereço para criar'),
    ('Não aplicavel', 'Não aplicável'),
    ('Ideal para candidaturas, estagios e programas de formacao.', 'Ideal para candidaturas, estágios e programas de formação.'),
    ('Apoia registos offline/assistidos e valida dados basicos.', 'Apoia registos offline/assistidos e valida dados básicos.'),
    ('Preciso acompanhar indicadores e relatarios.', 'Preciso acompanhar indicadores e relatórios.'),
    ('pelo formulario.', 'pelo formulário.'),
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
