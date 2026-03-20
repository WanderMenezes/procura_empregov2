from pathlib import Path
import re

BASE = Path(r'c:\xampp\htdocs\procura_empregov2')

PHRASE_REPLACEMENTS = [
    ('Obrigat\u00e9rio', 'Obrigat\u00f3rio'),
    ('obrigat\u00e9rio', 'obrigat\u00f3rio'),
    ('Obrigat\u00e9rios', 'Obrigat\u00f3rios'),
    ('obrigat\u00e9rios', 'obrigat\u00f3rios'),
    ('in?cio', 'in\u00edcio'),
    ('est?', 'est\u00e1'),
    ('at\u00e9n??o', 'aten\u00e7\u00e3o'),
    ('\u00e9ssencial', 'essencial'),
    ('\u00e9ssenciais', 'essenciais'),
    ('f\u00e1cilitar', 'facilitar'),
    ('p\u00fablica\u00e7\u00e3o', 'publica\u00e7\u00e3o'),
    ('P\u00fablica\u00e7\u00e3o', 'Publica\u00e7\u00e3o'),
    ('p\u00fablica\u00e7\u00f5es', 'publica\u00e7\u00f5es'),
    ('P\u00fablica\u00e7\u00f5es', 'Publica\u00e7\u00f5es'),
    ('p\u00fablicada', 'publicada'),
    ('P\u00fablicada', 'Publicada'),
    ('p\u00fablicadas', 'publicadas'),
    ('P\u00fablicadas', 'Publicadas'),
    ('p\u00fablicado', 'publicado'),
    ('P\u00fablicado', 'Publicado'),
    ('p\u00fablicados', 'publicados'),
    ('P\u00fablicados', 'Publicados'),
    ('p\u00fablicar', 'publicar'),
    ('P\u00fablicar', 'Publicar'),
    ('p\u00fablicam', 'publicam'),
    ('P\u00fablicam', 'Publicam'),
    ('P\u00fablica vagas', 'Publica vagas'),
    ('p\u00fablica vagas', 'publica vagas'),
    ('P\u00fablica a empresa', 'Publica a empresa'),
    ('p\u00fablica a empresa', 'publica a empresa'),
    ('Revej\u00e1', 'Reveja'),
    ('vej\u00e1', 'veja'),
    ('perfil e p\u00fablico', 'perfil \u00e9 p\u00fablico'),
    ('perfil e de empresa', 'perfil \u00e9 de empresa'),
    ('s\u00f3 e partilhado', 's\u00f3 \u00e9 partilhado'),
    ('passo seguinte normal e completar', 'passo seguinte normal \u00e9 completar'),
    ('resto do formulario', 'resto do formul\u00e1rio'),
    ('formulario offline', 'formul\u00e1rio offline'),
    ('dados sao os primeiros', 'dados s\u00e3o os primeiros'),
    ('campos sao obrigat\u00f3rios', 'campos s\u00e3o obrigat\u00f3rios'),
    ('o que esta ativo', 'o que est\u00e1 ativo'),
    ('ja est\u00e1', 'j\u00e1 est\u00e1'),
    ('ja foi', 'j\u00e1 foi'),
    ('ja pode', 'j\u00e1 pode'),
    ('nao existem', 'n\u00e3o existem'),
    ('nao existe', 'n\u00e3o existe'),
    ('nao informado', 'n\u00e3o informado'),
    ('nao definida', 'n\u00e3o definida'),
    ('nao definido', 'n\u00e3o definido'),
    ('nao definidos', 'n\u00e3o definidos'),
    ('nao informada', 'n\u00e3o informada'),
    ('nao foi', 'n\u00e3o foi'),
    ('nao queres', 'n\u00e3o queres'),
    ('nao tem', 'n\u00e3o tem'),
    ('Nao informado', 'N\u00e3o informado'),
    ('Nao definida', 'N\u00e3o definida'),
    ('Nao definido', 'N\u00e3o definido'),
    ('Nao definidos', 'N\u00e3o definidos'),
    ('Nao informada', 'N\u00e3o informada'),
    ('Nao foi', 'N\u00e3o foi'),
    ('Nao existem', 'N\u00e3o existem'),
    ('Nao existe', 'N\u00e3o existe'),
]

WORD_PATTERNS = [
    (r'\b\u00fatilizador\b', 'utilizador'),
    (r'\b\u00datilizador\b', 'Utilizador'),
    (r'\b\u00fatilizadores\b', 'utilizadores'),
    (r'\b\u00datilizadores\b', 'Utilizadores'),
    (r'\bSao\b', 'S\u00e3o'),
    (r'\bPrincipe\b', 'Pr\u00edncipe'),
    (r'\bNao\b', 'N\u00e3o'),
    (r'\bnao\b', 'n\u00e3o'),
    (r'\bJa\b', 'J\u00e1'),
    (r'\bja\b', 'j\u00e1'),
    (r'\bAte\b', 'At\u00e9'),
    (r'\bate\b', 'at\u00e9'),
    (r'\bsao\b', 's\u00e3o'),
    (r'\bSao\b', 'S\u00e3o'),
    (r'\bestao\b', 'est\u00e3o'),
    (r'\bEstao\b', 'Est\u00e3o'),
    (r'\btelemovel\b', 'telem\u00f3vel'),
    (r'\bTelemovel\b', 'Telem\u00f3vel'),
    (r'\bformacao\b', 'forma\u00e7\u00e3o'),
    (r'\bFormacao\b', 'Forma\u00e7\u00e3o'),
    (r'\binstituicao\b', 'institui\u00e7\u00e3o'),
    (r'\bInstituicao\b', 'Institui\u00e7\u00e3o'),
    (r'\bdescricao\b', 'descri\u00e7\u00e3o'),
    (r'\bDescricao\b', 'Descri\u00e7\u00e3o'),
    (r'\blocalizacao\b', 'localiza\u00e7\u00e3o'),
    (r'\bLocalizacao\b', 'Localiza\u00e7\u00e3o'),
    (r'\bvisualizacao\b', 'visualiza\u00e7\u00e3o'),
    (r'\bVisualizacao\b', 'Visualiza\u00e7\u00e3o'),
    (r'\bconfirmacao\b', 'confirma\u00e7\u00e3o'),
    (r'\bConfirmacao\b', 'Confirma\u00e7\u00e3o'),
    (r'\brecuperacao\b', 'recupera\u00e7\u00e3o'),
    (r'\bRecuperacao\b', 'Recupera\u00e7\u00e3o'),
    (r'\bnotificacao\b', 'notifica\u00e7\u00e3o'),
    (r'\bNotificacao\b', 'Notifica\u00e7\u00e3o'),
    (r'\bnotificacoes\b', 'notifica\u00e7\u00f5es'),
    (r'\bNotificacoes\b', 'Notifica\u00e7\u00f5es'),
    (r'\btecnica\b', 't\u00e9cnica'),
    (r'\bTecnica\b', 'T\u00e9cnica'),
    (r'\btecnico\b', 't\u00e9cnico'),
    (r'\bTecnico\b', 'T\u00e9cnico'),
    (r'\btecnicos\b', 't\u00e9cnicos'),
    (r'\bTecnicos\b', 'T\u00e9cnicos'),
    (r'\bhistorico\b', 'hist\u00f3rico'),
    (r'\bHistorico\b', 'Hist\u00f3rico'),
    (r'\bacademico\b', 'acad\u00e9mico'),
    (r'\bAcademico\b', 'Acad\u00e9mico'),
    (r'\bacademica\b', 'acad\u00e9mica'),
    (r'\bAcademica\b', 'Acad\u00e9mica'),
    (r'\bconteudo\b', 'conte\u00fado'),
    (r'\bConteudo\b', 'Conte\u00fado'),
    (r'\bpolitica\b', 'pol\u00edtica'),
    (r'\bPolitica\b', 'Pol\u00edtica'),
    (r'\bperiodo\b', 'per\u00edodo'),
    (r'\bPeriodo\b', 'Per\u00edodo'),
    (r'\bduvidas\b', 'd\u00favidas'),
    (r'\bDuvidas\b', 'D\u00favidas'),
    (r'\barea\b', '\u00e1rea'),
    (r'\bArea\b', '\u00c1rea'),
    (r'\banalise\b', 'an\u00e1lise'),
    (r'\bAnalise\b', 'An\u00e1lise'),
    (r'\bmaximo\b', 'm\u00e1ximo'),
    (r'\bMaximo\b', 'M\u00e1ximo'),
    (r'\bproximo\b', 'pr\u00f3ximo'),
    (r'\bProximo\b', 'Pr\u00f3ximo'),
    (r'\bproximos\b', 'pr\u00f3ximos'),
    (r'\bProximos\b', 'Pr\u00f3ximos'),
    (r'\bproxima\b', 'pr\u00f3xima'),
    (r'\bProxima\b', 'Pr\u00f3xima'),
    (r'\bproximas\b', 'pr\u00f3ximas'),
    (r'\bProximas\b', 'Pr\u00f3ximas'),
    (r'\bnitida\b', 'n\u00edtida'),
    (r'\bNitida\b', 'N\u00edtida'),
    (r'\bfriccao\b', 'fric\u00e7\u00e3o'),
    (r'\bFriccao\b', 'Fric\u00e7\u00e3o'),
    (r'\bavancar\b', 'avan\u00e7ar'),
    (r'\bAvancar\b', 'Avan\u00e7ar'),
    (r'\bcomeca\b', 'come\u00e7a'),
    (r'\bComeca\b', 'Come\u00e7a'),
    (r'\bcomecar\b', 'come\u00e7ar'),
    (r'\bComecar\b', 'Come\u00e7ar'),
    (r'\bligacao\b', 'liga\u00e7\u00e3o'),
    (r'\bLigacao\b', 'Liga\u00e7\u00e3o'),
    (r'\bprotecao\b', 'prote\u00e7\u00e3o'),
    (r'\bProtecao\b', 'Prote\u00e7\u00e3o'),
    (r'\bconfiguracao\b', 'configura\u00e7\u00e3o'),
    (r'\bConfiguracao\b', 'Configura\u00e7\u00e3o'),
    (r'\batualizacao\b', 'atualiza\u00e7\u00e3o'),
    (r'\bAtualizacao\b', 'Atualiza\u00e7\u00e3o'),
    (r'\bavaliacao\b', 'avalia\u00e7\u00e3o'),
    (r'\bAvaliacao\b', 'Avalia\u00e7\u00e3o'),
    (r'\bpublicacao\b', 'publica\u00e7\u00e3o'),
    (r'\bPublicacao\b', 'Publica\u00e7\u00e3o'),
    (r'\bpublicacoes\b', 'publica\u00e7\u00f5es'),
    (r'\bPublicacoes\b', 'Publica\u00e7\u00f5es'),
    (r'\bapresentacao\b', 'apresenta\u00e7\u00e3o'),
    (r'\bApresentacao\b', 'Apresenta\u00e7\u00e3o'),
    (r'\bsituacao\b', 'situa\u00e7\u00e3o'),
    (r'\bSituacao\b', 'Situa\u00e7\u00e3o'),
    (r'\bvisualizacao\b', 'visualiza\u00e7\u00e3o'),
    (r'\bVisualizacao\b', 'Visualiza\u00e7\u00e3o'),
    (r'\bacao\b', 'a\u00e7\u00e3o'),
    (r'\bAcao\b', 'A\u00e7\u00e3o'),
    (r'\bacoes\b', 'a\u00e7\u00f5es'),
    (r'\bAcoes\b', 'A\u00e7\u00f5es'),
    (r'\bcorrecao\b', 'corre\u00e7\u00e3o'),
    (r'\bCorrecao\b', 'Corre\u00e7\u00e3o'),
    (r'\bcriterio\b', 'crit\u00e9rio'),
    (r'\bCriterio\b', 'Crit\u00e9rio'),
    (r'\bcriterios\b', 'crit\u00e9rios'),
    (r'\bCriterios\b', 'Crit\u00e9rios'),
    (r'\bestagio\b', 'est\u00e1gio'),
    (r'\bEstagio\b', 'Est\u00e1gio'),
    (r'\bestagios\b', 'est\u00e1gios'),
    (r'\bEstagios\b', 'Est\u00e1gios'),
    (r'\bpratica\b', 'pr\u00e1tica'),
    (r'\bPratica\b', 'Pr\u00e1tica'),
    (r'\bnumero\b', 'n\u00famero'),
    (r'\bNumero\b', 'N\u00famero'),
    (r'\badministracao\b', 'administra\u00e7\u00e3o'),
    (r'\bAdministracao\b', 'Administra\u00e7\u00e3o'),
    (r'\bdisponiveis\b', 'dispon\u00edveis'),
    (r'\bDisponiveis\b', 'Dispon\u00edveis'),
    (r'\bconfianca\b', 'confian\u00e7a'),
    (r'\bConfianca\b', 'Confian\u00e7a'),
    (r'\bmotiva[cç]ao\b', 'motiva\u00e7\u00e3o'),
    (r'\bMotiva[cç]ao\b', 'Motiva\u00e7\u00e3o'),
    (r'\bobservacao\b', 'observa\u00e7\u00e3o'),
    (r'\bObservacao\b', 'Observa\u00e7\u00e3o'),
    (r'\bsugestao\b', 'sugest\u00e3o'),
    (r'\bSugestao\b', 'Sugest\u00e3o'),
    (r'\brejeicao\b', 'rejei\u00e7\u00e3o'),
    (r'\bRejeicao\b', 'Rejei\u00e7\u00e3o'),
    (r'\bdecisao\b', 'decis\u00e3o'),
    (r'\bDecisao\b', 'Decis\u00e3o'),
    (r'\bespaco\b', 'espa\u00e7o'),
    (r'\bEspaco\b', 'Espa\u00e7o'),
    (r'\bdinamica\b', 'din\u00e2mica'),
    (r'\bDinamica\b', 'Din\u00e2mica'),
    (r'\breforcar\b', 'refor\u00e7ar'),
    (r'\bReforcar\b', 'Refor\u00e7ar'),
    (r'\bvao\b', 'v\u00e3o'),
    (r'\bVao\b', 'V\u00e3o'),
    (r'\bopcao\b', 'op\u00e7\u00e3o'),
    (r'\bOpcao\b', 'Op\u00e7\u00e3o'),
    (r'\bopcoes\b', 'op\u00e7\u00f5es'),
    (r'\bOpcoes\b', 'Op\u00e7\u00f5es'),
    (r'\bconteudo\b', 'conte\u00fado'),
    (r'\bConteudo\b', 'Conte\u00fado'),
    (r'\brap\u00eddamente\b', 'rapidamente'),
]

WHOLE_FILE_FIXES = [
    ('S\u00c3\u00a3o Tom\u00c3\u00a9', 'S\u00e3o Tom\u00e9'),
    ('Pr\u00c3\u00adncipe', 'Pr\u00edncipe'),
    ('at\u00c3\u00a9n\u00c3\u00a7\u00c3\u00a3o', 'aten\u00e7\u00e3o'),
]


def correct_text(text: str) -> str:
    result = text
    for raw, fixed in WHOLE_FILE_FIXES:
        result = result.replace(raw, fixed)
    for raw, fixed in PHRASE_REPLACEMENTS:
        result = result.replace(raw, fixed)
    for pattern, repl in WORD_PATTERNS:
        result = re.sub(pattern, repl, result)
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
            if any(ch in value for ch in ['#', '/', '\\']) or value.startswith(('bi-', 'id_', 'data-', 'btn', 'form-', '.', ':', 'http', 'page=')):
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
