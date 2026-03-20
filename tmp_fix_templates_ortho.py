from pathlib import Path
import re

BASE = Path(r'c:\xampp\htdocs\procura_empregov2')

PAIRS = [
    ('Sao Tome e Principe', 'S\u00e3o Tom\u00e9 e Pr\u00edncipe'),
    ('Sao Tome', 'S\u00e3o Tom\u00e9'),
    ('Principe', 'Pr\u00edncipe'),
    ('Nao', 'N\u00e3o'), ('nao', 'n\u00e3o'),
    ('Ja', 'J\u00e1'), ('ja', 'j\u00e1'),
    ('Ate', 'At\u00e9'), ('ate', 'at\u00e9'),
    ('Pagina', 'P\u00e1gina'), ('pagina', 'p\u00e1gina'), ('Paginas', 'P\u00e1ginas'), ('paginas', 'p\u00e1ginas'),
    ('Rapido', 'R\u00e1pido'), ('rapido', 'r\u00e1pido'), ('Rapida', 'R\u00e1pida'), ('rapida', 'r\u00e1pida'),
    ('Rapidos', 'R\u00e1pidos'), ('rapidos', 'r\u00e1pidos'), ('Rapidas', 'R\u00e1pidas'), ('rapidas', 'r\u00e1pidas'),
    ('Video', 'V\u00eddeo'), ('video', 'v\u00eddeo'), ('Videos', 'V\u00eddeos'), ('videos', 'v\u00eddeos'),
    ('Telemovel', 'Telem\u00f3vel'), ('telemovel', 'telem\u00f3vel'),
    ('Minimo', 'M\u00ednimo'), ('minimo', 'm\u00ednimo'),
    ('Publico', 'P\u00fablico'), ('publico', 'p\u00fablico'), ('Publicos', 'P\u00fablicos'), ('publicos', 'p\u00fablicos'),
    ('Publica', 'P\u00fablica'), ('publica', 'p\u00fablica'), ('Publicas', 'P\u00fablicas'), ('publicas', 'p\u00fablicas'),
    ('Concluido', 'Conclu\u00eddo'), ('concluido', 'conclu\u00eddo'), ('Concluida', 'Conclu\u00edda'), ('concluida', 'conclu\u00edda'),
    ('Concluidos', 'Conclu\u00eddos'), ('concluidos', 'conclu\u00eddos'), ('Concluidas', 'Conclu\u00eddas'), ('concluidas', 'conclu\u00eddas'),
    ('Disponivel', 'Dispon\u00edvel'), ('disponivel', 'dispon\u00edvel'), ('Disponiveis', 'Dispon\u00edveis'), ('disponiveis', 'dispon\u00edveis'),
    ('Visivel', 'Vis\u00edvel'), ('visivel', 'vis\u00edvel'), ('Visiveis', 'Vis\u00edveis'), ('visiveis', 'vis\u00edveis'),
    ('Possivel', 'Poss\u00edvel'), ('possivel', 'poss\u00edvel'), ('Possiveis', 'Poss\u00edveis'), ('possiveis', 'poss\u00edveis'),
    ('Experiencia', 'Experi\u00eancia'), ('experiencia', 'experi\u00eancia'), ('Experiencias', 'Experi\u00eancias'), ('experiencias', 'experi\u00eancias'),
    ('Educacao', 'Educa\u00e7\u00e3o'), ('educacao', 'educa\u00e7\u00e3o'),
    ('Informacao', 'Informa\u00e7\u00e3o'), ('informacao', 'informa\u00e7\u00e3o'), ('Informacoes', 'Informa\u00e7\u00f5es'), ('informacoes', 'informa\u00e7\u00f5es'),
    ('Localizacao', 'Localiza\u00e7\u00e3o'), ('localizacao', 'localiza\u00e7\u00e3o'),
    ('Organizacao', 'Organiza\u00e7\u00e3o'), ('organizacao', 'organiza\u00e7\u00e3o'),
    ('Descricao', 'Descri\u00e7\u00e3o'), ('descricao', 'descri\u00e7\u00e3o'), ('Descricoes', 'Descri\u00e7\u00f5es'), ('descricoes', 'descri\u00e7\u00f5es'),
    ('Validacao', 'Valida\u00e7\u00e3o'), ('validacao', 'valida\u00e7\u00e3o'),
    ('Aprovacao', 'Aprova\u00e7\u00e3o'), ('aprovacao', 'aprova\u00e7\u00e3o'),
    ('Selecao', 'Sele\u00e7\u00e3o'), ('selecao', 'sele\u00e7\u00e3o'),
    ('Gestao', 'Gest\u00e3o'), ('gestao', 'gest\u00e3o'),
    ('Atencao', 'Aten\u00e7\u00e3o'), ('atencao', 'aten\u00e7\u00e3o'),
    ('Tecnico', 'T\u00e9cnico'), ('tecnico', 't\u00e9cnico'), ('Tecnicos', 'T\u00e9cnicos'), ('tecnicos', 't\u00e9cnicos'),
    ('Tecnica', 'T\u00e9cnica'), ('tecnica', 't\u00e9cnica'), ('Tecnicas', 'T\u00e9cnicas'), ('tecnicas', 't\u00e9cnicas'),
    ('Historico', 'Hist\u00f3rico'), ('historico', 'hist\u00f3rico'),
    ('Academico', 'Acad\u00e9mico'), ('academico', 'acad\u00e9mico'), ('Academica', 'Acad\u00e9mica'), ('academica', 'acad\u00e9mica'),
    ('Conteudo', 'Conte\u00fado'), ('conteudo', 'conte\u00fado'),
    ('Autorizacao', 'Autoriza\u00e7\u00e3o'), ('autorizacao', 'autoriza\u00e7\u00e3o'),
    ('Relatorio', 'Relat\u00f3rio'), ('relatorio', 'relat\u00f3rio'), ('Relatorios', 'Relat\u00f3rios'), ('relatorios', 'relat\u00f3rios'),
    ('Estatistica', 'Estat\u00edstica'), ('estatistica', 'estat\u00edstica'), ('Estatisticas', 'Estat\u00edsticas'), ('estatisticas', 'estat\u00edsticas'),
    ('Politica', 'Pol\u00edtica'), ('politica', 'pol\u00edtica'),
    ('Periodo', 'Per\u00edodo'), ('periodo', 'per\u00edodo'),
    ('Duvidas', 'D\u00favidas'), ('duvidas', 'd\u00favidas'),
    ('Area', '\u00c1rea'), ('area', '\u00e1rea'), ('Areas', '\u00c1reas'), ('areas', '\u00e1reas'),
    ('Maximo', 'M\u00e1ximo'), ('maximo', 'm\u00e1ximo'),
    ('Analise', 'An\u00e1lise'), ('analise', 'an\u00e1lise'),
    ('Obrigatorio', 'Obrigat\u00f3rio'), ('obrigatorio', 'obrigat\u00f3rio'), ('Obrigatorios', 'Obrigat\u00f3rios'), ('obrigatorios', 'obrigat\u00f3rios'),
    ('Especifico', 'Espec\u00edfico'), ('especifico', 'espec\u00edfico'), ('Especifica', 'Espec\u00edfica'), ('especifica', 'espec\u00edfica'),
    ('Especificos', 'Espec\u00edficos'), ('especificos', 'espec\u00edficos'), ('Especificas', 'Espec\u00edficas'), ('especificas', 'espec\u00edficas'),
    ('Intencao', 'Inten\u00e7\u00e3o'), ('intencao', 'inten\u00e7\u00e3o'),
    ('Proximo', 'Pr\u00f3ximo'), ('proximo', 'pr\u00f3ximo'), ('Proximos', 'Pr\u00f3ximos'), ('proximos', 'pr\u00f3ximos'),
    ('Nitida', 'N\u00edtida'), ('nitida', 'n\u00edtida'),
    ('Friccao', 'Fric\u00e7\u00e3o'), ('friccao', 'fric\u00e7\u00e3o'),
    ('Avancar', 'Avan\u00e7ar'), ('avancar', 'avan\u00e7ar'),
    ('Comeca', 'Come\u00e7a'), ('comeca', 'come\u00e7a'), ('Comecar', 'Come\u00e7ar'), ('comecar', 'come\u00e7ar'),
    ('Ligacao', 'Liga\u00e7\u00e3o'), ('ligacao', 'liga\u00e7\u00e3o'),
    ('Protecao', 'Prote\u00e7\u00e3o'), ('protecao', 'prote\u00e7\u00e3o'),
    ('Configuracao', 'Configura\u00e7\u00e3o'), ('configuracao', 'configura\u00e7\u00e3o'),
    ('Atualizacao', 'Atualiza\u00e7\u00e3o'), ('atualizacao', 'atualiza\u00e7\u00e3o'),
    ('Avaliacao', 'Avalia\u00e7\u00e3o'), ('avaliacao', 'avalia\u00e7\u00e3o'),
    ('Publicacao', 'Publica\u00e7\u00e3o'), ('publicacao', 'publica\u00e7\u00e3o'), ('Publicacoes', 'Publica\u00e7\u00f5es'), ('publicacoes', 'publica\u00e7\u00f5es'),
    ('Apresentacao', 'Apresenta\u00e7\u00e3o'), ('apresentacao', 'apresenta\u00e7\u00e3o'),
    ('Situacao', 'Situa\u00e7\u00e3o'), ('situacao', 'situa\u00e7\u00e3o'), ('Situacoes', 'Situa\u00e7\u00f5es'), ('situacoes', 'situa\u00e7\u00f5es'),
    ('Util', '\u00datil'), ('util', '\u00fatil'),
    ('Facil', 'F\u00e1cil'), ('facil', 'f\u00e1cil'),
    ('Critico', 'Cr\u00edtico'), ('critico', 'cr\u00edtico'),
    ('Notificacao', 'Notifica\u00e7\u00e3o'), ('notificacao', 'notifica\u00e7\u00e3o'), ('Notificacoes', 'Notifica\u00e7\u00f5es'), ('notificacoes', 'notifica\u00e7\u00f5es'),
    ('Visualizacao', 'Visualiza\u00e7\u00e3o'), ('visualizacao', 'visualiza\u00e7\u00e3o'),
    ('Verificacao', 'Verifica\u00e7\u00e3o'), ('verificacao', 'verifica\u00e7\u00e3o'), ('Verificacoes', 'Verifica\u00e7\u00f5es'), ('verificacoes', 'verifica\u00e7\u00f5es'),
    ('Confirmacao', 'Confirma\u00e7\u00e3o'), ('confirmacao', 'confirma\u00e7\u00e3o'),
    ('Recuperacao', 'Recupera\u00e7\u00e3o'), ('recuperacao', 'recupera\u00e7\u00e3o'),
    ('Instituicao', 'Institui\u00e7\u00e3o'), ('instituicao', 'institui\u00e7\u00e3o'),
    ('Curriculo', 'Curr\u00edculo'), ('curriculo', 'curr\u00edculo'),
    ('Funcao', 'Fun\u00e7\u00e3o'), ('funcao', 'fun\u00e7\u00e3o'),
    ('Sequencia', 'Sequ\u00eancia'), ('sequencia', 'sequ\u00eancia'),
    ('Formacao', 'Forma\u00e7\u00e3o'), ('formacao', 'forma\u00e7\u00e3o'),
    ('Adesao', 'Ades\u00e3o'), ('adesao', 'ades\u00e3o'),
    ('Operacao', 'Opera\u00e7\u00e3o'), ('operacao', 'opera\u00e7\u00e3o'),
    ('Aderencia', 'Ader\u00eancia'), ('aderencia', 'ader\u00eancia'),
    ('Tracao', 'Tra\u00e7\u00e3o'), ('tracao', 'tra\u00e7\u00e3o'),
    ('Motivacao', 'Motiva\u00e7\u00e3o'), ('motivacao', 'motiva\u00e7\u00e3o'),
    ('Observacao', 'Observa\u00e7\u00e3o'), ('observacao', 'observa\u00e7\u00e3o'),
    ('Circulacao', 'Circula\u00e7\u00e3o'), ('circulacao', 'circula\u00e7\u00e3o'),
    ('Confianca', 'Confian\u00e7a'), ('confianca', 'confian\u00e7a'),
    ('Recomendacoes', 'Recomenda\u00e7\u00f5es'), ('recomendacoes', 'recomenda\u00e7\u00f5es'),
    ('Acao', 'A\u00e7\u00e3o'), ('acao', 'a\u00e7\u00e3o'), ('Acoes', 'A\u00e7\u00f5es'), ('acoes', 'a\u00e7\u00f5es'),
    ('Interacao', 'Intera\u00e7\u00e3o'), ('interacao', 'intera\u00e7\u00e3o'),
    ('Correcao', 'Corre\u00e7\u00e3o'), ('correcao', 'corre\u00e7\u00e3o'),
    ('Criterio', 'Crit\u00e9rio'), ('criterio', 'crit\u00e9rio'), ('Criterios', 'Crit\u00e9rios'), ('criterios', 'crit\u00e9rios'),
    ('Estagio', 'Est\u00e1gio'), ('estagio', 'est\u00e1gio'), ('Estagios', 'Est\u00e1gios'), ('estagios', 'est\u00e1gios'),
    ('Pratica', 'Pr\u00e1tica'), ('pratica', 'pr\u00e1tica'), ('Pratico', 'Pr\u00e1tico'), ('pratico', 'pr\u00e1tico'), ('Praticos', 'Pr\u00e1ticos'), ('praticos', 'pr\u00e1ticos'),
    ('Ultima', '\u00daltima'), ('ultima', '\u00faltima'), ('Ultimas', '\u00daltimas'), ('ultimas', '\u00faltimas'),
    ('Numero', 'N\u00famero'), ('numero', 'n\u00famero'),
    ('Administracao', 'Administra\u00e7\u00e3o'), ('administracao', 'administra\u00e7\u00e3o'),
    ('Demonstracao', 'Demonstra\u00e7\u00e3o'), ('demonstracao', 'demonstra\u00e7\u00e3o'), ('Demonstracoes', 'Demonstra\u00e7\u00f5es'), ('demonstracoes', 'demonstra\u00e7\u00f5es'),
    ('Contem', 'Cont\u00e9m'), ('contem', 'cont\u00e9m'),
    ('Sera', 'Ser\u00e1'), ('sera', 'ser\u00e1'),
    ('Teras', 'Ter\u00e1s'), ('teras', 'ter\u00e1s'),
    ('Evolucao', 'Evolu\u00e7\u00e3o'), ('evolucao', 'evolu\u00e7\u00e3o'),
    ('Distribuicao', 'Distribui\u00e7\u00e3o'), ('distribuicao', 'distribui\u00e7\u00e3o'),
    ('Atras', 'Atr\u00e1s'), ('atras', 'atr\u00e1s'),
    ('Ultimos', '\u00daltimos'), ('ultimos', '\u00faltimos'),
    ('Unico', '\u00danico'), ('unico', '\u00fanico'),
    ('Sugestao', 'Sugest\u00e3o'), ('sugestao', 'sugest\u00e3o'),
    ('Associacao', 'Associa\u00e7\u00e3o'), ('associacao', 'associa\u00e7\u00e3o'),
]

WHOLE_FILE_FIXES = [
    ('S\u00c3\u00a3o Tom\u00c3\u00a9 e Pr\u00c3\u00adncipe', 'S\u00e3o Tom\u00e9 e Pr\u00edncipe'),
    ('S\u00c3\u00a3o Tom\u00c3\u00a9', 'S\u00e3o Tom\u00e9'),
    ('Pr\u00c3\u00adncipe', 'Pr\u00edncipe'),
    ('est\u00c3\u00a1gios', 'est\u00e1gios'),
    ('forma\u00c3\u00a7\u00c3\u00a3o', 'forma\u00e7\u00e3o'),
    ('informa\u00c3\u00a7\u00c3\u00a3o', 'informa\u00e7\u00e3o'),
]


def broken(value: str) -> str:
    return ''.join(ch if ord(ch) < 128 else '?' for ch in value)


def correct_text(text: str) -> str:
    result = text
    for raw, fixed in PAIRS:
        result = result.replace(raw, fixed)
        result = result.replace(broken(fixed), fixed)
    phrase_fixes = [
        ('Se es', 'Se \u00e9s'), ('se es', 'se \u00e9s'),
        (' ja esta ', ' j\u00e1 est\u00e1 '), (' Ja esta ', ' J\u00e1 est\u00e1 '),
        (' nao e ', ' n\u00e3o \u00e9 '), (' Nao e ', ' N\u00e3o \u00e9 '),
        (' nao foi ', ' n\u00e3o foi '), (' Nao foi ', ' N\u00e3o foi '),
        (' nao existem ', ' n\u00e3o existem '), (' Nao existem ', ' N\u00e3o existem '),
        (' nao existe ', ' n\u00e3o existe '), (' Nao existe ', ' N\u00e3o existe '),
        (' nao conseguiu ', ' n\u00e3o conseguiu '), (' Nao conseguiu ', ' N\u00e3o conseguiu '),
        (' nao pode ', ' n\u00e3o pode '), (' Nao pode ', ' N\u00e3o pode '),
        (' ja pode ', ' j\u00e1 pode '), (' Ja pode ', ' J\u00e1 pode '),
        (' ja foi ', ' j\u00e1 foi '), (' Ja foi ', ' J\u00e1 foi '),
        (' so ', ' s\u00f3 '), (' So ', ' S\u00f3 '),
        (' ha ', ' h\u00e1 '), (' Ha ', ' H\u00e1 '),
        ('Voltar a pesquisa', 'Voltar \u00e0 pesquisa'),
        ('conta tecnica', 'conta t\u00e9cnica'), ('Conta tecnica', 'Conta t\u00e9cnica'),
        ('Tecnico PNUD', 'T\u00e9cnico PNUD'),
        ('Operador Distrital (Associacao/Parceiro)', 'Operador Distrital (Associa\u00e7\u00e3o/Parceiro)'),
        ('Leitura rapida', 'Leitura r\u00e1pida'), ('Ajuda rapida', 'Ajuda r\u00e1pida'),
        ('Resumo rapido', 'Resumo r\u00e1pido'), ('Sugestao rapida', 'Sugest\u00e3o r\u00e1pida'),
        ('Leituras rapidas', 'Leituras r\u00e1pidas'),
        ('publicadas ha pouco', 'publicadas h\u00e1 pouco'),
    ]
    for raw, fixed in phrase_fixes:
        result = result.replace(raw, fixed)
        result = result.replace(broken(fixed), fixed)
    return result


def correct_template_text_chunks(value: str) -> str:
    parts = re.split(r'({%.*?%}|{{.*?}}|{#.*?#})', value, flags=re.S)
    out = []
    for part in parts:
        if re.fullmatch(r'{%.*?%}|{{.*?}}|{#.*?#}', part or '', flags=re.S):
            out.append(part)
        else:
            out.append(correct_text(part))
    return ''.join(out)


def replace_attrs(content: str) -> str:
    attr_re = re.compile(r'(?P<prefix>\b(?:placeholder|title|aria-label|alt|content)\s*=\s*)(?P<quote>["\'])(?P<value>.*?)(?P=quote)', re.S)
    def repl(m):
        value = m.group('value')
        if '{%' in value or '{{' in value:
            return m.group(0)
        return f"{m.group('prefix')}{m.group('quote')}{correct_text(value)}{m.group('quote')}"
    return attr_re.sub(repl, content)


def replace_text_nodes(content: str) -> str:
    text_re = re.compile(r'>([^<]+)<', re.S)
    def repl(m):
        return '>' + correct_template_text_chunks(m.group(1)) + '<'
    return text_re.sub(repl, content)


def replace_script_strings(content: str) -> str:
    script_re = re.compile(r'(<script\b[^>]*>)(.*?)(</script>)', re.S | re.I)
    string_re = re.compile(r'(["\'])(.*?)(?<!\\)\1', re.S)
    def script_block(m):
        start, body, end = m.groups()
        def str_repl(sm):
            quote, value = sm.groups()
            if any(ch in value for ch in ['#', '/', '\\']) or value.startswith(('bi-', 'id_', 'data-', 'btn', 'form-', '.', ':', 'http')):
                return sm.group(0)
            fixed = correct_text(value)
            return f'{quote}{fixed}{quote}'
        return start + string_re.sub(str_repl, body) + end
    return script_re.sub(script_block, content)

changed = []
for path in sorted((BASE / 'templates').rglob('*.html')):
    text = path.read_text(encoding='utf-8')
    updated = text
    for raw, fixed in WHOLE_FILE_FIXES:
        updated = updated.replace(raw, fixed)
    updated = replace_attrs(updated)
    updated = replace_text_nodes(updated)
    updated = replace_script_strings(updated)
    if updated != text:
        path.write_text(updated, encoding='utf-8')
        changed.append(str(path.relative_to(BASE)))

print('\n'.join(changed))
print(f'TOTAL={len(changed)}')
