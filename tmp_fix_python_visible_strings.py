from pathlib import Path

base = Path(r'c:\xampp\htdocs\procura_empregov2')
changes = [
    ('accounts/forms.py', [
        ('Formulario do admin para editar dados principais de um útilizador.', 'Formulário do admin para editar dados principais de um utilizador.'),
        ('O NIF e obrigatório para empresas.', 'O NIF é obrigatório para empresas.'),
        ('O número do BI e obrigatório para candidatos.', 'O número do BI é obrigatório para candidatos.'),
    ]),
    ('accounts/views.py', [
        ('Marcar todas as notificaÃ§Ãµes do útilizador como lidas', 'Marcar todas as notificações do utilizador como lidas'),
        ('Todas as notificaÃ§Ãµes foram marcadas como lidas.', 'Todas as notificações foram marcadas como lidas.'),
        ('NÃ£o havia notificaÃ§Ãµes por ler.', 'Não havia notificações por ler.'),
        ('Eliminar notificaÃ§Ã£o', 'Eliminar notificação'),
    ]),
    ('dashboard/forms.py', [
        ('Ficheiro de importação gerado pelo formulario offline', 'Ficheiro de importação gerado pelo formulário offline'),
        ('Importe o ficheiro JSON gerado pelo formulario offline.', 'Importe o ficheiro JSON gerado pelo formulário offline.'),
    ]),
    ('dashboard/views.py', [
        ('O nome e obrigatório no registo offline.', 'O nome é obrigatório no registo offline.'),
        ('O telemóvel e obrigatório no registo offline.', 'O telemóvel é obrigatório no registo offline.'),
        ('O distrito e obrigatório no registo offline.', 'O distrito é obrigatório no registo offline.'),
        ('Já existe um útilizador com este telemóvel.', 'Já existe um utilizador com este telemóvel.'),
        ('Já existe um útilizador com este email.', 'Já existe um utilizador com este email.'),
        ('O número do BI e obrigatório para registos offline de jovens.', 'O número do BI é obrigatório para registos offline de jovens.'),
        ('Já existe um útilizador com este número de BI.', 'Já existe um utilizador com este número de BI.'),
        ('O NIF e obrigatório para registos offline de empresas.', 'O NIF é obrigatório para registos offline de empresas.'),
        ('Já existe um útilizador com este NIF.', 'Já existe um utilizador com este NIF.'),
        ('Lista de útilizadores', 'Lista de utilizadores'),
        ('Útilizador criado com sucesso.', 'Utilizador criado com sucesso.'),
        ('Editar dados principais de um útilizador pelo painel admin.', 'Editar dados principais de um utilizador pelo painel admin.'),
        ('Útilizador atualizado com sucesso.', 'Utilizador atualizado com sucesso.'),
        ('Ativar/desativar útilizador', 'Ativar/desativar utilizador'),
        ('Útilizador {} com sucesso!', 'Utilizador {} com sucesso!'),
        ('Área para gerar e importar registos offline de útilizadores.', 'Área para gerar e importar registos offline de utilizadores.'),
        ('Importar ficheiro offline e criar o registo do útilizador.', 'Importar ficheiro offline e criar o registo do utilizador.'),
    ]),
]
for rel_path, items in changes:
    path = base / rel_path
    text = path.read_text(encoding='utf-8')
    updated = text
    for raw, fixed in items:
        updated = updated.replace(raw, fixed)
    if updated != text:
        path.write_text(updated, encoding='utf-8')
        print(rel_path)
