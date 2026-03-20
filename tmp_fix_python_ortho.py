from pathlib import Path
import ast
import io
import re
import tokenize

BASE = Path(r'c:\xampp\htdocs\procura_empregov2')
FILES = [
    BASE / 'accounts' / 'forms.py',
    BASE / 'accounts' / 'views.py',
    BASE / 'companies' / 'forms.py',
    BASE / 'companies' / 'views.py',
    BASE / 'dashboard' / 'forms.py',
    BASE / 'dashboard' / 'views.py',
    BASE / 'profiles' / 'forms.py',
    BASE / 'profiles' / 'views.py',
]

PAIRS = [
    ('Nao', 'N\u00e3o'), ('nao', 'n\u00e3o'), ('Ja', 'J\u00e1'), ('ja', 'j\u00e1'), ('Ate', 'At\u00e9'), ('ate', 'at\u00e9'),
    ('Rapido', 'R\u00e1pido'), ('rapido', 'r\u00e1pido'), ('Rapida', 'R\u00e1pida'), ('rapida', 'r\u00e1pida'),
    ('Video', 'V\u00eddeo'), ('video', 'v\u00eddeo'), ('Pagina', 'P\u00e1gina'), ('pagina', 'p\u00e1gina'),
    ('Telemovel', 'Telem\u00f3vel'), ('telemovel', 'telem\u00f3vel'), ('Minimo', 'M\u00ednimo'), ('minimo', 'm\u00ednimo'),
    ('Publico', 'P\u00fablico'), ('publico', 'p\u00fablico'), ('Concluido', 'Conclu\u00eddo'), ('concluido', 'conclu\u00eddo'),
    ('Disponivel', 'Dispon\u00edvel'), ('disponivel', 'dispon\u00edvel'), ('Visivel', 'Vis\u00edvel'), ('visivel', 'vis\u00edvel'),
    ('Possivel', 'Poss\u00edvel'), ('possivel', 'poss\u00edvel'), ('Experiencia', 'Experi\u00eancia'), ('experiencia', 'experi\u00eancia'),
    ('Educacao', 'Educa\u00e7\u00e3o'), ('educacao', 'educa\u00e7\u00e3o'), ('Informacao', 'Informa\u00e7\u00e3o'), ('informacao', 'informa\u00e7\u00e3o'),
    ('Informacoes', 'Informa\u00e7\u00f5es'), ('informacoes', 'informa\u00e7\u00f5es'), ('Localizacao', 'Localiza\u00e7\u00e3o'), ('localizacao', 'localiza\u00e7\u00e3o'),
    ('Organizacao', 'Organiza\u00e7\u00e3o'), ('organizacao', 'organiza\u00e7\u00e3o'), ('Descricao', 'Descri\u00e7\u00e3o'), ('descricao', 'descri\u00e7\u00e3o'),
    ('Validacao', 'Valida\u00e7\u00e3o'), ('validacao', 'valida\u00e7\u00e3o'), ('Aprovacao', 'Aprova\u00e7\u00e3o'), ('aprovacao', 'aprova\u00e7\u00e3o'),
    ('Selecao', 'Sele\u00e7\u00e3o'), ('selecao', 'sele\u00e7\u00e3o'), ('Gestao', 'Gest\u00e3o'), ('gestao', 'gest\u00e3o'),
    ('Atencao', 'Aten\u00e7\u00e3o'), ('atencao', 'aten\u00e7\u00e3o'), ('Tecnico', 'T\u00e9cnico'), ('tecnico', 't\u00e9cnico'),
    ('Tecnica', 'T\u00e9cnica'), ('tecnica', 't\u00e9cnica'), ('Historico', 'Hist\u00f3rico'), ('historico', 'hist\u00f3rico'),
    ('Academico', 'Acad\u00e9mico'), ('academico', 'acad\u00e9mico'), ('Conteudo', 'Conte\u00fado'), ('conteudo', 'conte\u00fado'),
    ('Autorizacao', 'Autoriza\u00e7\u00e3o'), ('autorizacao', 'autoriza\u00e7\u00e3o'), ('Relatorio', 'Relat\u00f3rio'), ('relatorio', 'relat\u00f3rio'),
    ('Relatorios', 'Relat\u00f3rios'), ('relatorios', 'relat\u00f3rios'), ('Estatisticas', 'Estat\u00edsticas'), ('estatisticas', 'estat\u00edsticas'),
    ('Politica', 'Pol\u00edtica'), ('politica', 'pol\u00edtica'), ('Periodo', 'Per\u00edodo'), ('periodo', 'per\u00edodo'),
    ('Duvidas', 'D\u00favidas'), ('duvidas', 'd\u00favidas'), ('Area', '\u00c1rea'), ('area', '\u00e1rea'), ('Areas', '\u00c1reas'), ('areas', '\u00e1reas'),
    ('Maximo', 'M\u00e1ximo'), ('maximo', 'm\u00e1ximo'), ('Analise', 'An\u00e1lise'), ('analise', 'an\u00e1lise'), ('Obrigatorio', 'Obrigat\u00f3rio'), ('obrigatorio', 'obrigat\u00f3rio'),
    ('Especifico', 'Espec\u00edfico'), ('especifico', 'espec\u00edfico'), ('Especifica', 'Espec\u00edfica'), ('especifica', 'espec\u00edfica'),
    ('Intencao', 'Inten\u00e7\u00e3o'), ('intencao', 'inten\u00e7\u00e3o'), ('Proximo', 'Pr\u00f3ximo'), ('proximo', 'pr\u00f3ximo'),
    ('Nitida', 'N\u00edtida'), ('nitida', 'n\u00edtida'), ('Friccao', 'Fric\u00e7\u00e3o'), ('friccao', 'fric\u00e7\u00e3o'),
    ('Avancar', 'Avan\u00e7ar'), ('avancar', 'avan\u00e7ar'), ('Comeca', 'Come\u00e7a'), ('comeca', 'come\u00e7a'), ('Comecar', 'Come\u00e7ar'), ('comecar', 'come\u00e7ar'),
    ('Ligacao', 'Liga\u00e7\u00e3o'), ('ligacao', 'liga\u00e7\u00e3o'), ('Protecao', 'Prote\u00e7\u00e3o'), ('protecao', 'prote\u00e7\u00e3o'),
    ('Configuracao', 'Configura\u00e7\u00e3o'), ('configuracao', 'configura\u00e7\u00e3o'), ('Atualizacao', 'Atualiza\u00e7\u00e3o'), ('atualizacao', 'atualiza\u00e7\u00e3o'),
    ('Avaliacao', 'Avalia\u00e7\u00e3o'), ('avaliacao', 'avalia\u00e7\u00e3o'), ('Publicacao', 'Publica\u00e7\u00e3o'), ('publicacao', 'publica\u00e7\u00e3o'),
    ('Apresentacao', 'Apresenta\u00e7\u00e3o'), ('apresentacao', 'apresenta\u00e7\u00e3o'), ('Situacao', 'Situa\u00e7\u00e3o'), ('situacao', 'situa\u00e7\u00e3o'),
    ('Util', '\u00datil'), ('util', '\u00fatil'), ('Facil', 'F\u00e1cil'), ('facil', 'f\u00e1cil'), ('Notificacoes', 'Notifica\u00e7\u00f5es'), ('notificacoes', 'notifica\u00e7\u00f5es'),
    ('Visualizacao', 'Visualiza\u00e7\u00e3o'), ('visualizacao', 'visualiza\u00e7\u00e3o'), ('Instituicao', 'Institui\u00e7\u00e3o'), ('instituicao', 'institui\u00e7\u00e3o'),
    ('Curriculo', 'Curr\u00edculo'), ('curriculo', 'curr\u00edculo'), ('Funcao', 'Fun\u00e7\u00e3o'), ('funcao', 'fun\u00e7\u00e3o'), ('Sequencia', 'Sequ\u00eancia'), ('sequencia', 'sequ\u00eancia'),
    ('Formacao', 'Forma\u00e7\u00e3o'), ('formacao', 'forma\u00e7\u00e3o'), ('Operacao', 'Opera\u00e7\u00e3o'), ('operacao', 'opera\u00e7\u00e3o'), ('Confianca', 'Confian\u00e7a'), ('confianca', 'confian\u00e7a'),
    ('Acao', 'A\u00e7\u00e3o'), ('acao', 'a\u00e7\u00e3o'), ('Acoes', 'A\u00e7\u00f5es'), ('acoes', 'a\u00e7\u00f5es'), ('Estagio', 'Est\u00e1gio'), ('estagio', 'est\u00e1gio'),
    ('Pratica', 'Pr\u00e1tica'), ('pratica', 'pr\u00e1tica'), ('Numero', 'N\u00famero'), ('numero', 'n\u00famero'), ('Administracao', 'Administra\u00e7\u00e3o'), ('administracao', 'administra\u00e7\u00e3o'),
    ('Motivacao', 'Motiva\u00e7\u00e3o'), ('motivacao', 'motiva\u00e7\u00e3o'), ('Observacao', 'Observa\u00e7\u00e3o'), ('observacao', 'observa\u00e7\u00e3o'), ('Sugestao', 'Sugest\u00e3o'), ('sugestao', 'sugest\u00e3o'),
]

WHOLE_FILE_FIXES = [
    ('S\u00c3\u00a3o Tom\u00c3\u00a9', 'S\u00e3o Tom\u00e9'), ('Pr\u00c3\u00adncipe', 'Pr\u00edncipe'), ('est\u00c3\u00a1gios', 'est\u00e1gios'), ('forma\u00c3\u00a7\u00c3\u00a3o', 'forma\u00e7\u00e3o'),
]


def broken(value: str) -> str:
    return ''.join(ch if ord(ch) < 128 else '?' for ch in value)


def correct_text(text: str) -> str:
    result = text
    for raw, fixed in PAIRS:
        result = result.replace(raw, fixed)
        result = result.replace(broken(fixed), fixed)
    for raw, fixed in WHOLE_FILE_FIXES:
        result = result.replace(raw, fixed)
    phrase_fixes = [
        ('Se es', 'Se \u00e9s'), ('se es', 'se \u00e9s'), (' ja esta ', ' j\u00e1 est\u00e1 '), (' Ja esta ', ' J\u00e1 est\u00e1 '),
        (' nao e ', ' n\u00e3o \u00e9 '), (' Nao e ', ' N\u00e3o \u00e9 '), (' nao foi ', ' n\u00e3o foi '), (' Nao foi ', ' N\u00e3o foi '),
        (' nao pode ', ' n\u00e3o pode '), (' Nao pode ', ' N\u00e3o pode '), (' ja pode ', ' j\u00e1 pode '), (' Ja pode ', ' J\u00e1 pode '),
        (' so ', ' s\u00f3 '), (' So ', ' S\u00f3 '), (' ha ', ' h\u00e1 '), (' Ha ', ' H\u00e1 '), ('Leitura rapida', 'Leitura r\u00e1pida'),
        ('Resumo rapido', 'Resumo r\u00e1pido'), ('Sugestao rapida', 'Sugest\u00e3o r\u00e1pida'), ('Conta tecnica', 'Conta t\u00e9cnica'), ('Tecnico PNUD', 'T\u00e9cnico PNUD'),
    ]
    for raw, fixed in phrase_fixes:
        result = result.replace(raw, fixed)
        result = result.replace(broken(fixed), fixed)
    return result


def should_fix(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if not value:
        return False
    if '\n' in value and len(value.strip()) == 0:
        return False
    if (' ' not in value) and ('?' not in value) and ('\u00c3' not in value):
        return False
    if any(marker in value for marker in ['__', 'http://', 'https://', 'profiles:', 'accounts:', 'companies:', 'dashboard:', '/']) and ' ' not in value:
        return False
    return True


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    for raw, fixed in WHOLE_FILE_FIXES:
        text = text.replace(raw, fixed)
    tokens = []
    changed = False
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.STRING:
            s = tok.string
            prefix_match = re.match(r'([rubfRUBF]*)([\'\"]{1,3})(.*)([\'\"]{1,3})$', s, re.S)
            if prefix_match:
                prefix = prefix_match.group(1)
                if 'f' not in prefix.lower() and 'r' not in prefix.lower() and 'b' not in prefix.lower():
                    try:
                        value = ast.literal_eval(s)
                    except Exception:
                        value = None
                    if isinstance(value, str) and should_fix(value):
                        fixed = correct_text(value)
                        if fixed != value:
                            s = repr(fixed)
                            changed = True
            tok = tokenize.TokenInfo(tok.type, s, tok.start, tok.end, tok.line)
        tokens.append(tok)
    if changed:
        path.write_text(tokenize.untokenize(tokens), encoding='utf-8')
    return changed

changed_files = []
for file_path in FILES:
    if fix_file(file_path):
        changed_files.append(str(file_path.relative_to(BASE)))

print('\n'.join(changed_files))
print(f'TOTAL={len(changed_files)}')
