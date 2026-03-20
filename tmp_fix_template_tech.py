from pathlib import Path

base = Path(r'c:\xampp\htdocs\procura_empregov2')
changes = [
    ('templates/accounts/register.html', [
        ('id_bi_n\u00famero', 'id_bi_numero'),
        ('setRuleStat\u00e9', 'setRuleState'),
        ('updat\u00e9PasswordRules', 'updatePasswordRules'),
        ('updat\u00e9PhotoPreview', 'updatePhotoPreview'),
        ('URL.creat\u00e9ObjectURL', 'URL.createObjectURL'),
    ]),
    ('templates/dashboard/user_list.html', [
        ('id_bi_n\u00famero', 'id_bi_numero'),
        ('updat\u00e9Creat\u00e9UserForm', 'updateCreateUserForm'),
    ]),
    ('templates/profiles/wizard.html', [
        ('birthDat\u00e9Input', 'birthDateInput'),
        ('birthDat\u00e9', 'birthDate'),
        ('Dat\u00e9', 'Date'),
        ('temExperi\u00eancia', 'temExperiencia'),
        ('id_tem_experi\u00eancia', 'id_tem_experiencia'),
        ('experi\u00eanciaFields', 'experienciaFields'),
        ('experi\u00eancia_fields', 'experiencia_fields'),
        ('toggleExperi\u00eancia', 'toggleExperiencia'),
        ('setAutosaveStat\u00e9', 'setAutosaveState'),
        ('updat\u00e9Age', 'updateAge'),
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/profiles/experience_form.html', [
        ('toggleEndDat\u00e9', 'toggleEndDate'),
    ]),
    ('templates/companies/job_form.html', [
        ('formatDat\u00e9', 'formatDate'),
    ]),
    ('templates/companies/search_youth.html', [
        ('updat\u00e9SelectionStat\u00e9', 'updateSelectionState'),
        ('indeterminat\u00e9', 'indeterminate'),
        ('aj\u00e1x-page', 'ajax-page'),
        ('attachAj\u00e1xP\u00e1gination', 'attachAjaxPagination'),
        ('pushStat\u00e9', 'pushState'),
        ('popstat\u00e9', 'popstate'),
        ('Aj\u00e1x na pagina\u00e7\u00e3o', 'Ajax na pagina\u00e7\u00e3o'),
    ]),
    ('templates/dashboard/reports.html', [
        ('syncMinDat\u00e9', 'syncMinDate'),
    ]),
    ('templates/base/base.html', [
        ('relat\u00e9dTarget', 'relatedTarget'),
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/profiles/vagas_disponiveis.html', [
        ('relat\u00e9dTarget', 'relatedTarget'),
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/profiles/my_applications.html', [
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/profiles/assisted_register.html', [
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/companies/complete_profile.html', [
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/core/help.html', [
        ('In?cio', 'In\u00edcio'),
    ]),
    ('templates/accounts/notifications.html', [
        ('Eliminar esta notificacao?', 'Eliminar esta notifica\u00e7\u00e3o?'),
    ]),
    ('templates/profiles/detail.html', [
        ('Tens a certeza que queres remover esta formacao?', 'Tens a certeza que queres remover esta forma\u00e7\u00e3o?'),
        ('Tens a certeza que queres remover esta experiencia?', 'Tens a certeza que queres remover esta experi\u00eancia?'),
    ]),
    ('templates/dashboard/offline_registration_form_document.html', [
        ("observa\u00e7\u00f5es: getValue('observa\u00e7\u00f5es')", "observacoes: getValue('observacoes')"),
        ("data.bi_n\u00famero = getValue('bi_n\u00famero');", "data.bi_numero = getValue('bi_numero');"),
        ("data.situa\u00e7\u00e3o_atual = getValue('situa\u00e7\u00e3o_atual');", "data.situacao_atual = getValue('situacao_atual');"),
        ("data.\u00e1rea_forma\u00e7\u00e3o = getValue('\u00e1rea_forma\u00e7\u00e3o');", "data.area_formacao = getValue('area_formacao');"),
        ("data.institui\u00e7\u00e3o = getValue('institui\u00e7\u00e3o');", "data.instituicao = getValue('instituicao');"),
        ("data.descri\u00e7\u00e3o = getValue('descri\u00e7\u00e3o');", "data.descricao = getValue('descricao');"),
        ('document.creat\u00e9Element', 'document.createElement'),
        ('URL.creat\u00e9ObjectURL', 'URL.createObjectURL'),
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
