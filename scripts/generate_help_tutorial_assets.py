from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import django
import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base_nacional_jovens.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402

from companies.models import Application, Company, ContactRequest, JobPost  # noqa: E402
from core.models import District, Skill  # noqa: E402
from profiles.models import Education, Experience, YouthProfile, YouthSkill  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402


EDGE_EXECUTABLE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
SCREEN_DIR = BASE_DIR / "static" / "help" / "tutorial-frames"
VIDEO_PATH = BASE_DIR / "static" / "help" / "help-tutorial.mp4"
POSTER_PATH = BASE_DIR / "static" / "help" / "help-tutorial-poster.jpg"
FPS = 24
SCENE_SECONDS = 3.8
TRANSITION_SECONDS = 0.5
CANVAS_SIZE = (1280, 720)
CONTENT_SIZE = (1140, 444)
BROWSER_BOX = (60, 40, 1220, 540)
CAPTION_BOX = (60, 560, 1220, 680)
PASSWORD = "Tutorial123!"


@dataclass(frozen=True)
class SceneSpec:
    key: str
    title: str
    caption: str
    start_y: float
    end_y: float


SCENES = [
    SceneSpec(
        key="01-home",
        title="1. Explorar a pagina inicial",
        caption="A homepage apresenta o objetivo da plataforma, os caminhos principais e oportunidades em destaque.",
        start_y=0.08,
        end_y=0.32,
    ),
    SceneSpec(
        key="02-register",
        title="2. Criar conta com o perfil certo",
        caption="O registo orienta jovem e empresa logo no inicio, com campos e ajuda adaptados ao tipo de conta.",
        start_y=0.12,
        end_y=0.38,
    ),
    SceneSpec(
        key="03-login",
        title="3. Entrar rapidamente",
        caption="O login aceita telemovel ou email e encaminha cada utilizador para a sua area correta.",
        start_y=0.10,
        end_y=0.18,
    ),
    SceneSpec(
        key="04-wizard",
        title="4. Completar o perfil passo a passo",
        caption="O wizard do jovem mostra progresso, dicas e secoes curtas para preencher com menos friccao.",
        start_y=0.08,
        end_y=0.22,
    ),
    SceneSpec(
        key="05-jobs",
        title="5. Procurar vagas com afinidade",
        caption="A lista de oportunidades combina filtros rapidos com sugestoes baseadas no perfil do jovem.",
        start_y=0.08,
        end_y=0.28,
    ),
    SceneSpec(
        key="06-company",
        title="6. Gerir o lado da empresa",
        caption="Empresas acompanham vagas, pedidos de contacto e indicadores num painel unico.",
        start_y=0.08,
        end_y=0.20,
    ),
]


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                Path(r"C:\Windows\Fonts\segoeuib.ttf"),
                Path(r"C:\Windows\Fonts\arialbd.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                Path(r"C:\Windows\Fonts\segoeui.ttf"),
                Path(r"C:\Windows\Fonts\arial.ttf"),
            ]
        )
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=text_font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def crop_scene_image(source: Image.Image, progress: float) -> Image.Image:
    scene = SCENES_BY_NAME[source.info["scene_key"]]
    target_w, target_h = CONTENT_SIZE
    src_w, src_h = source.size
    target_ratio = target_w / target_h
    crop_w = src_w
    crop_h = int(round(crop_w / target_ratio))
    if crop_h > src_h:
        crop_h = src_h
        crop_w = int(round(crop_h * target_ratio))

    focus = scene.start_y + (scene.end_y - scene.start_y) * ease_in_out(progress)
    max_top = max(src_h - crop_h, 0)
    top = int(round(clamp(focus * src_h - crop_h / 2, 0, max_top)))
    left = max((src_w - crop_w) // 2, 0)

    cropped = source.crop((left, top, left + crop_w, top + crop_h))
    zoom = 1.0 + 0.04 * ease_in_out(progress)
    resized = cropped.resize(
        (int(round(target_w * zoom)), int(round(target_h * zoom))),
        Image.Resampling.LANCZOS,
    )
    if resized.size[0] == target_w and resized.size[1] == target_h:
        return resized

    extra_x = max(resized.size[0] - target_w, 0)
    extra_y = max(resized.size[1] - target_h, 0)
    offset_x = extra_x // 2
    offset_y = extra_y // 2
    return resized.crop((offset_x, offset_y, offset_x + target_w, offset_y + target_h))


def render_scene_frame(source: Image.Image, scene: SceneSpec, progress: float) -> Image.Image:
    canvas = Image.new("RGB", CANVAS_SIZE, "#081824")

    bg = source.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(22))
    overlay = Image.new("RGBA", CANVAS_SIZE, (4, 17, 28, 155))
    canvas = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    shadow = Image.new("RGBA", (BROWSER_BOX[2] - BROWSER_BOX[0] + 28, BROWSER_BOX[3] - BROWSER_BOX[1] + 30), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((0, 0, shadow.size[0], shadow.size[1]), radius=30, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.paste(shadow, (BROWSER_BOX[0] - 14, BROWSER_BOX[1] + 10), shadow)

    browser = Image.new("RGBA", (BROWSER_BOX[2] - BROWSER_BOX[0], BROWSER_BOX[3] - BROWSER_BOX[1]), (12, 28, 43, 255))
    browser_draw = ImageDraw.Draw(browser)
    browser_draw.rounded_rectangle((0, 0, browser.size[0], browser.size[1]), radius=28, fill=(10, 28, 44, 245))
    browser_draw.rounded_rectangle((0, 0, browser.size[0], 46), radius=28, fill=(7, 20, 33, 255))
    browser_draw.rectangle((0, 23, browser.size[0], 46), fill=(7, 20, 33, 255))

    for index, color in enumerate(((255, 104, 108), (255, 201, 87), (45, 211, 111))):
        x = 22 + index * 16
        browser_draw.ellipse((x, 16, x + 10, 26), fill=color)

    browser_draw.rounded_rectangle((76, 10, browser.size[0] - 22, 34), radius=12, fill=(255, 255, 255, 18))
    url_text = "127.0.0.1:8000"
    browser_draw.text((92, 14), url_text, font=font(13, bold=False), fill=(220, 232, 242))

    cropped = crop_scene_image(source, progress)
    mask = rounded_mask(CONTENT_SIZE, radius=20)
    browser.paste(cropped, (10, 46), mask=mask)
    canvas.paste(browser.convert("RGB"), (BROWSER_BOX[0], BROWSER_BOX[1]))

    caption_shadow = Image.new("RGBA", (CAPTION_BOX[2] - CAPTION_BOX[0] + 24, CAPTION_BOX[3] - CAPTION_BOX[1] + 24), (0, 0, 0, 0))
    ImageDraw.Draw(caption_shadow).rounded_rectangle((0, 0, caption_shadow.size[0], caption_shadow.size[1]), radius=28, fill=(0, 0, 0, 110))
    caption_shadow = caption_shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.paste(caption_shadow, (CAPTION_BOX[0] - 12, CAPTION_BOX[1] + 10), caption_shadow)

    caption = Image.new("RGBA", (CAPTION_BOX[2] - CAPTION_BOX[0], CAPTION_BOX[3] - CAPTION_BOX[1]), (10, 28, 44, 214))
    caption_draw = ImageDraw.Draw(caption)
    caption_draw.rounded_rectangle((0, 0, caption.size[0], caption.size[1]), radius=26, fill=(10, 28, 44, 214))
    caption_draw.rounded_rectangle((20, 18, 182, 48), radius=15, fill=(14, 111, 147, 255))
    caption_draw.text((32, 25), "Tutorial real", font=font(16, bold=True), fill="white")

    title_font = font(32, bold=True)
    body_font = font(18, bold=False)
    caption_draw.text((24, 60), scene.title, font=title_font, fill="white")

    wrapped = wrap_text(caption_draw, scene.caption, body_font, 760)
    line_y = 98
    for line in wrapped[:2]:
        caption_draw.text((24, line_y), line, font=body_font, fill=(214, 226, 236))
        line_y += 26

    counter_font = font(18, bold=True)
    right_text = f"{SCENES.index(scene) + 1}/{len(SCENES)}"
    right_bbox = caption_draw.textbbox((0, 0), right_text, font=counter_font)
    right_x = caption.size[0] - (right_bbox[2] - right_bbox[0]) - 40
    caption_draw.text((right_x, 26), right_text, font=counter_font, fill=(185, 214, 231))

    dot_y = 92
    dot_start = caption.size[0] - 212
    for index in range(len(SCENES)):
        x = dot_start + index * 28
        fill = (42, 160, 107, 255) if index == SCENES.index(scene) else (255, 255, 255, 55)
        caption_draw.ellipse((x, dot_y, x + 12, dot_y + 12), fill=fill)

    caption_draw.text((caption.size[0] - 248, 120), "Guia rapido da interface", font=font(16, bold=False), fill=(185, 214, 231))
    canvas.paste(caption.convert("RGB"), (CAPTION_BOX[0], CAPTION_BOX[1]))
    return canvas


def seed_demo_data() -> dict[str, str]:
    user_model = get_user_model()
    district = District.objects.order_by("id").first()
    if district is None:
        district = District.objects.create(codigo="AG", nome="Agua Grande")

    skills = list(Skill.objects.order_by("id")[:3])
    if len(skills) < 3:
        defaults = [
            ("Atendimento ao cliente", "TRA"),
            ("Canva", "TEC"),
            ("Informatica", "TEC"),
        ]
        for name, skill_type in defaults[len(skills):]:
            skills.append(
                Skill.objects.create(nome=name, tipo=skill_type, aprovada=True)
            )

    youth_user, _ = user_model.objects.get_or_create(
        telefone="+2397001001",
        defaults={
            "nome": "Maria Tutorial",
            "email": "tutorial.jovem@local.test",
            "perfil": user_model.ProfileType.JOVEM,
            "distrito": district,
            "is_active": True,
            "is_verified": True,
            "consentimento_dados": True,
            "consentimento_contacto": True,
            "data_consentimento": timezone.now(),
            "bi_numero": "TUT-0001",
        },
    )
    youth_user.nome = "Maria Tutorial"
    youth_user.email = "tutorial.jovem@local.test"
    youth_user.perfil = user_model.ProfileType.JOVEM
    youth_user.distrito = district
    youth_user.is_active = True
    youth_user.is_verified = True
    youth_user.consentimento_dados = True
    youth_user.consentimento_contacto = True
    youth_user.data_consentimento = timezone.now()
    youth_user.bi_numero = "TUT-0001"
    youth_user.set_password(PASSWORD)
    youth_user.save()

    youth_profile, _ = YouthProfile.objects.get_or_create(user=youth_user)
    youth_profile.data_nascimento = date(2002, 8, 15)
    youth_profile.sexo = "F"
    youth_profile.localidade = "Ponte Mina"
    youth_profile.contacto_alternativo = "+239 980 1001"
    youth_profile.situacao_atual = "PEM"
    youth_profile.disponibilidade = "SIM"
    youth_profile.interesse_setorial = ["TIC", "SER", "ADM"]
    youth_profile.preferencia_oportunidade = "EMP"
    youth_profile.sobre = (
        "Jovem com interesse em atendimento digital, ferramentas de escritorio "
        "e apoio administrativo."
    )
    youth_profile.completo = True
    youth_profile.validado = True
    youth_profile.visivel = True
    youth_profile.consentimento_sms = True
    youth_profile.consentimento_whatsapp = True
    youth_profile.consentimento_email = True
    youth_profile.wizard_step = 4
    youth_profile.wizard_data = {}
    youth_profile.save()

    education, _ = Education.objects.get_or_create(
        profile=youth_profile,
        instituicao="Centro de Formacao Tutorial",
        defaults={
            "nivel": "TEC",
            "area_formacao": "TIC",
            "ano": 2025,
            "curso": "Tecnico de Informatica",
        },
    )
    education.nivel = "TEC"
    education.area_formacao = "TIC"
    education.ano = 2025
    education.curso = "Tecnico de Informatica"
    education.save()

    experience, _ = Experience.objects.get_or_create(
        profile=youth_profile,
        entidade="Balcao Jovem Digital",
        cargo="Assistente de atendimento",
        defaults={
            "inicio": date.today() - timedelta(days=260),
            "fim": None,
            "atual": True,
            "descricao": "Apoio a candidatos, triagem de pedidos e organizacao de dados basicos.",
        },
    )
    experience.inicio = date.today() - timedelta(days=260)
    experience.fim = None
    experience.atual = True
    experience.descricao = "Apoio a candidatos, triagem de pedidos e organizacao de dados basicos."
    experience.save()

    YouthSkill.objects.filter(profile=youth_profile).exclude(skill__in=skills).delete()
    for skill in skills:
        YouthSkill.objects.get_or_create(profile=youth_profile, skill=skill, defaults={"nivel": 2})

    company_user, _ = user_model.objects.get_or_create(
        telefone="+2397001002",
        defaults={
            "nome": "Studio Tutorial",
            "email": "tutorial.empresa@local.test",
            "perfil": user_model.ProfileType.EMPRESA,
            "nome_empresa": "Studio Tutorial",
            "nif": "TUT-EMP-01",
            "distrito": district,
            "is_active": True,
            "is_verified": True,
        },
    )
    company_user.nome = "Studio Tutorial"
    company_user.email = "tutorial.empresa@local.test"
    company_user.perfil = user_model.ProfileType.EMPRESA
    company_user.nome_empresa = "Studio Tutorial"
    company_user.nif = "TUT-EMP-01"
    company_user.distrito = district
    company_user.is_active = True
    company_user.is_verified = True
    company_user.set_password(PASSWORD)
    company_user.save()

    company_profile, _ = Company.objects.get_or_create(
        user=company_user,
        defaults={
            "nome": "Studio Tutorial",
            "nif": "TUT-EMP-01",
            "setor": ["TIC", "SER"],
            "descricao": "Empresa demo para o tutorial da plataforma.",
            "telefone": "+239 700 1002",
            "email": "tutorial.empresa@local.test",
            "website": "https://studio-tutorial.local",
            "distrito": district,
            "endereco": "Avenida Marginal, Sao Tome",
            "ativa": True,
            "verificada": True,
        },
    )
    company_profile.nome = "Studio Tutorial"
    company_profile.nif = "TUT-EMP-01"
    company_profile.setor = ["TIC", "SER"]
    company_profile.descricao = "Empresa demo para o tutorial da plataforma."
    company_profile.telefone = "+239 700 1002"
    company_profile.email = "tutorial.empresa@local.test"
    company_profile.website = "https://studio-tutorial.local"
    company_profile.distrito = district
    company_profile.endereco = "Avenida Marginal, Sao Tome"
    company_profile.ativa = True
    company_profile.verificada = True
    company_profile.save()

    job_one, _ = JobPost.objects.get_or_create(
        company=company_profile,
        titulo="Assistente administrativo junior",
        defaults={
            "descricao": "Apoio ao atendimento, organizacao de documentos e comunicacao com candidatos.",
            "requisitos": "Boa comunicacao, nocao de ferramentas digitais e disponibilidade imediata.",
            "tipo": "EMP",
            "numero_vagas": 2,
            "distrito": district,
            "local_trabalho": "Sao Tome",
            "nivel_educacao": "SEC",
            "area_formacao": "ADM",
            "experiencia_minima": 0,
            "salario": "A combinar",
            "beneficios": "Formacao inicial e acompanhamento.",
            "estado": "ATIVA",
            "data_fecho": date.today() + timedelta(days=18),
        },
    )
    job_one.descricao = "Apoio ao atendimento, organizacao de documentos e comunicacao com candidatos."
    job_one.requisitos = "Boa comunicacao, nocao de ferramentas digitais e disponibilidade imediata."
    job_one.tipo = "EMP"
    job_one.numero_vagas = 2
    job_one.distrito = district
    job_one.local_trabalho = "Sao Tome"
    job_one.nivel_educacao = "SEC"
    job_one.area_formacao = "ADM"
    job_one.experiencia_minima = 0
    job_one.salario = "A combinar"
    job_one.beneficios = "Formacao inicial e acompanhamento."
    job_one.estado = "ATIVA"
    job_one.data_fecho = date.today() + timedelta(days=18)
    job_one.save()

    job_two, _ = JobPost.objects.get_or_create(
        company=company_profile,
        titulo="Operador de apoio digital",
        defaults={
            "descricao": "Acompanhamento de pedidos, verificacao de documentos e suporte a usuarios.",
            "requisitos": "Conforto com computador, boa escrita e vontade de aprender.",
            "tipo": "EMP",
            "numero_vagas": 1,
            "distrito": district,
            "local_trabalho": "Sao Tome",
            "nivel_educacao": "TEC",
            "area_formacao": "TIC",
            "experiencia_minima": 0,
            "salario": "Bolsa mensal",
            "beneficios": "Mentoria e horario flexivel.",
            "estado": "ATIVA",
            "data_fecho": date.today() + timedelta(days=10),
        },
    )
    job_two.descricao = "Acompanhamento de pedidos, verificacao de documentos e suporte a usuarios."
    job_two.requisitos = "Conforto com computador, boa escrita e vontade de aprender."
    job_two.tipo = "EMP"
    job_two.numero_vagas = 1
    job_two.distrito = district
    job_two.local_trabalho = "Sao Tome"
    job_two.nivel_educacao = "TEC"
    job_two.area_formacao = "TIC"
    job_two.experiencia_minima = 0
    job_two.salario = "Bolsa mensal"
    job_two.beneficios = "Mentoria e horario flexivel."
    job_two.estado = "ATIVA"
    job_two.data_fecho = date.today() + timedelta(days=10)
    job_two.save()

    application, _ = Application.objects.get_or_create(
        job=job_two,
        youth=youth_profile,
        defaults={
            "estado": "EM_ANALISE",
            "mensagem": "Tenho interesse na vaga e disponibilidade imediata.",
        },
    )
    application.estado = "EM_ANALISE"
    application.mensagem = "Tenho interesse na vaga e disponibilidade imediata."
    application.save()

    contact_request, _ = ContactRequest.objects.get_or_create(
        company=company_profile,
        youth=youth_profile,
        defaults={
            "motivo": "Perfil alinhado com as vagas administrativas e digitais.",
            "estado": "PENDENTE",
        },
    )
    contact_request.motivo = "Perfil alinhado com as vagas administrativas e digitais."
    contact_request.estado = "PENDENTE"
    contact_request.save()

    return {
        "youth_phone": youth_user.telefone,
        "company_phone": company_user.telefone,
        "password": PASSWORD,
    }


def wait_and_screenshot(page, path: Path, full_page: bool = True) -> None:
    page.wait_for_timeout(600)
    page.screenshot(path=str(path), full_page=full_page, animations="disabled")


def login(page, username: str, password: str) -> None:
    page.goto("http://127.0.0.1:8000/accounts/entrar/", wait_until="networkidle")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def capture_screens(credentials: dict[str, str]) -> None:
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    if not EDGE_EXECUTABLE.exists():
        raise FileNotFoundError(f"Edge executable not found at {EDGE_EXECUTABLE}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(EDGE_EXECUTABLE),
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        public_context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            locale="pt-PT",
            color_scheme="light",
        )
        page = public_context.new_page()

        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        wait_and_screenshot(page, SCREEN_DIR / "01-home.png")

        page.goto("http://127.0.0.1:8000/accounts/registar/", wait_until="networkidle")
        page.check('input[name="perfil"][value="JO"]', force=True)
        page.fill('input[name="nome"]', "Maria Tutorial")
        page.fill('input[name="telefone"]', "+239 700 1001")
        page.fill('input[name="email"]', "tutorial.jovem@local.test")
        page.fill('input[name="bi_numero"]', "TUT-0001")
        page.fill('input[name="password1"]', PASSWORD)
        page.fill('input[name="password2"]', PASSWORD)
        page.check('input[name="consentimento_dados"]', force=True)
        page.check('input[name="consentimento_contacto"]', force=True)
        wait_and_screenshot(page, SCREEN_DIR / "02-register.png")

        page.goto("http://127.0.0.1:8000/accounts/entrar/", wait_until="networkidle")
        page.fill('input[name="username"]', credentials["youth_phone"])
        page.fill('input[name="password"]', credentials["password"])
        wait_and_screenshot(page, SCREEN_DIR / "03-login.png")
        public_context.close()

        youth_context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            locale="pt-PT",
            color_scheme="light",
        )
        youth_page = youth_context.new_page()
        login(youth_page, credentials["youth_phone"], credentials["password"])
        youth_page.goto("http://127.0.0.1:8000/profiles/completar-perfil/passo/2/", wait_until="networkidle")
        wait_and_screenshot(youth_page, SCREEN_DIR / "04-wizard.png")
        youth_page.goto("http://127.0.0.1:8000/profiles/vagas-disponiveis/", wait_until="networkidle")
        wait_and_screenshot(youth_page, SCREEN_DIR / "05-jobs.png")
        youth_context.close()

        company_context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            locale="pt-PT",
            color_scheme="light",
        )
        company_page = company_context.new_page()
        login(company_page, credentials["company_phone"], credentials["password"])
        company_page.goto("http://127.0.0.1:8000/companies/painel/", wait_until="networkidle")
        wait_and_screenshot(company_page, SCREEN_DIR / "06-company.png")
        company_context.close()

        browser.close()


def build_video() -> None:
    VIDEO_PATH.parent.mkdir(parents=True, exist_ok=True)
    scene_frames: list[tuple[SceneSpec, Image.Image]] = []
    for scene in SCENES:
        image_path = SCREEN_DIR / f"{scene.key}.png"
        if not image_path.exists():
            raise FileNotFoundError(f"Missing screenshot: {image_path}")
        image = Image.open(image_path).convert("RGB")
        image.info["scene_key"] = scene.key
        scene_frames.append((scene, image))

    writer = imageio.get_writer(
        str(VIDEO_PATH),
        fps=FPS,
        codec="libx264",
        quality=7,
        ffmpeg_log_level="error",
        output_params=["-pix_fmt", "yuv420p"],
    )

    try:
        first_frame = None
        scene_frame_count = int(SCENE_SECONDS * FPS)
        transition_frame_count = int(TRANSITION_SECONDS * FPS)
        previous_rendered = None

        for index, (scene, source) in enumerate(scene_frames):
            for frame_index in range(scene_frame_count):
                progress = frame_index / max(scene_frame_count - 1, 1)
                rendered = render_scene_frame(source, scene, progress)
                if first_frame is None:
                    first_frame = rendered.copy()
                writer.append_data(np.asarray(rendered))
                previous_rendered = rendered

            if index == len(scene_frames) - 1:
                continue

            next_scene, next_source = scene_frames[index + 1]
            current_hold = render_scene_frame(source, scene, 1.0)
            next_hold = render_scene_frame(next_source, next_scene, 0.0)
            for frame_index in range(transition_frame_count):
                blend = frame_index / max(transition_frame_count - 1, 1)
                blended = Image.blend(current_hold, next_hold, ease_in_out(blend))
                writer.append_data(np.asarray(blended))
                previous_rendered = blended

        if previous_rendered is not None:
            for _ in range(int(0.8 * FPS)):
                writer.append_data(np.asarray(previous_rendered))

        if first_frame is not None:
            first_frame.save(POSTER_PATH, format="JPEG", quality=90, optimize=True)
    finally:
        writer.close()


SCENES_BY_NAME = {scene.key: scene for scene in SCENES}


def main() -> None:
    credentials = seed_demo_data()
    capture_screens(credentials)
    build_video()
    print(f"Video written to {VIDEO_PATH}")
    print(f"Poster written to {POSTER_PATH}")


if __name__ == "__main__":
    main()



