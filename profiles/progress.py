"""Helpers to summarize youth profile completion from saved or draft data."""

import json

from .models import YouthProfile


PROFILE_STEP_FIELDS = {
    '1': ['nome', 'telefone', 'email', 'contacto_alternativo', 'distrito', 'data_nascimento', 'sexo', 'localidade'],
    '2': ['nivel', 'area_formacao', 'instituicao', 'ano', 'curso', 'skills', 'idiomas'],
    '3': ['situacao_atual', 'disponibilidade', 'interesse_setorial', 'preferencia_oportunidade', 'sobre'],
    '4': ['cv', 'certificado', 'bi', 'visivel', 'consentimento_sms', 'consentimento_whatsapp', 'consentimento_email'],
}

PROFILE_STEP_META = {
    '1': {'title': 'Dados pessoais', 'short_title': 'Dados pessoais'},
    '2': {'title': 'Educacao, skills e idiomas', 'short_title': 'Educacao e skills'},
    '3': {'title': 'Experiencia e interesses', 'short_title': 'Experiencia'},
    '4': {'title': 'Documentos e consentimentos', 'short_title': 'Documentos'},
}

_ALWAYS_COUNT_BOOL = {
    'visivel',
    'consentimento_sms',
    'consentimento_whatsapp',
    'consentimento_email',
}


def _build_progress_snapshot_from_step_stats(step_stats: dict) -> dict:
    total_fields = sum(item['total'] for item in step_stats.values())
    filled_fields = sum(item['filled'] for item in step_stats.values())
    total_missing = sum(item['missing'] for item in step_stats.values())
    completed_steps = sum(1 for item in step_stats.values() if item['filled'] >= item['total'])
    progress = int((filled_fields / total_fields) * 100) if total_fields else 0

    next_step = None
    for step in PROFILE_STEP_FIELDS:
        item = step_stats.get(step, {})
        if item.get('filled', 0) < item.get('total', 0):
            meta = PROFILE_STEP_META.get(step, {})
            next_step = {
                'step': step,
                'title': meta.get('title', ''),
                'short_title': meta.get('short_title', meta.get('title', '')),
                'filled': item.get('filled', 0),
                'total': item.get('total', 0),
                'missing': item.get('missing', 0),
            }
            break

    return {
        'step_stats': step_stats,
        'progress': progress,
        'filled_fields': filled_fields,
        'total_fields': total_fields,
        'total_missing': total_missing,
        'completed_steps': completed_steps,
        'total_steps': len(PROFILE_STEP_FIELDS),
        'next_step': next_step,
    }


def _normalize_wizard_data(wizard_data) -> dict:
    if isinstance(wizard_data, dict):
        return wizard_data
    return {}


def _parse_idioma_payload(value):
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except (TypeError, ValueError):
            return []
        if isinstance(loaded, list):
            return [item for item in loaded if isinstance(item, dict)]
    return []


def compute_wizard_step_progress(wizard_data: dict) -> dict:
    """Compute progress using draft wizard data stored in JSON."""
    wizard_data = _normalize_wizard_data(wizard_data)
    result = {}

    for step, fields in PROFILE_STEP_FIELDS.items():
        total = len(fields)
        filled = 0
        step_data = wizard_data.get(step, {})
        if not isinstance(step_data, dict):
            step_data = {}

        for field_name in fields:
            if field_name == 'idiomas':
                payload = _parse_idioma_payload(step_data.get('idiomas_data'))
                if payload:
                    filled += 1
                    continue
                has_partial_idioma = any(
                    step_data.get(f'idioma_{index}_nome') or step_data.get(f'idioma_{index}_dominio')
                    for index in range(1, 5)
                )
                if has_partial_idioma:
                    filled += 1
                continue

            if field_name == 'area_formacao':
                value = step_data.get(field_name)
                if value == 'OUT':
                    if step_data.get('outra_area_formacao'):
                        filled += 1
                    continue

            value = step_data.get(field_name)
            if isinstance(value, bool):
                if field_name in _ALWAYS_COUNT_BOOL or value:
                    filled += 1
            elif isinstance(value, list):
                if value:
                    filled += 1
            elif value not in (None, '', False):
                filled += 1

        result[step] = {
            'filled': filled,
            'total': total,
            'missing': max(total - filled, 0),
        }

    return result


def compute_saved_profile_step_progress(profile: YouthProfile) -> dict:
    """Compute filled, total and missing counts for a saved profile."""
    education_items = list(profile.education.all())
    education = education_items[0] if education_items else None
    document_types = {item.tipo for item in profile.documents.all()}
    has_skills = bool(list(profile.youth_skills.all()))

    result = {}
    for step, fields in PROFILE_STEP_FIELDS.items():
        total = len(fields)
        filled = 0

        for field_name in fields:
            value = None
            if step == '1':
                if field_name == 'nome':
                    value = getattr(profile.user, 'nome', '')
                elif field_name == 'telefone':
                    value = getattr(profile.user, 'telefone', '')
                elif field_name == 'email':
                    value = getattr(profile.user, 'email', '')
                elif field_name == 'distrito':
                    value = getattr(profile.user, 'distrito', None)
                elif field_name == 'data_nascimento':
                    value = getattr(profile, 'data_nascimento', None)
                elif field_name == 'sexo':
                    value = getattr(profile, 'sexo', '')
                elif field_name == 'localidade':
                    value = getattr(profile, 'localidade', '')
                elif field_name == 'contacto_alternativo':
                    value = getattr(profile, 'contacto_alternativo', '')
            elif step == '2':
                if field_name == 'skills':
                    value = has_skills
                elif field_name == 'idiomas':
                    value = bool(profile.idiomas_detalhados)
                elif field_name == 'area_formacao':
                    if education and education.area_formacao == 'OUT':
                        value = education.outra_area_formacao or ''
                    else:
                        value = getattr(education, field_name, None) if education else None
                else:
                    value = getattr(education, field_name, None) if education else None
            elif step == '3':
                value = getattr(profile, field_name, None)
            elif step == '4':
                if field_name == 'cv':
                    value = 'CV' in document_types
                elif field_name == 'certificado':
                    value = 'CERT' in document_types
                elif field_name == 'bi':
                    value = 'BI' in document_types
                else:
                    value = getattr(profile, field_name, False)

            if isinstance(value, bool):
                if field_name in _ALWAYS_COUNT_BOOL or value:
                    filled += 1
            elif isinstance(value, (list, tuple)):
                if value:
                    filled += 1
            elif value not in (None, '', False):
                filled += 1

        missing = max(total - filled, 0)
        result[step] = {'filled': filled, 'total': total, 'missing': missing}

    return result


def compute_profile_step_progress(profile: YouthProfile) -> dict:
    """Compute progress using draft data when available, otherwise saved data."""
    if not profile.completo and _normalize_wizard_data(profile.wizard_data):
        return compute_wizard_step_progress(profile.wizard_data)
    return compute_saved_profile_step_progress(profile)


def build_wizard_progress_snapshot(wizard_data: dict) -> dict:
    """Return a compact progress snapshot for draft wizard data."""
    return _build_progress_snapshot_from_step_stats(
        compute_wizard_step_progress(wizard_data)
    )


def build_profile_progress_snapshot(profile: YouthProfile) -> dict:
    """Return a compact progress snapshot for a profile and its persisted draft."""
    return _build_progress_snapshot_from_step_stats(
        compute_profile_step_progress(profile)
    )
