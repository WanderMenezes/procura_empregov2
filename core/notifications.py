from django.contrib.auth import get_user_model

from .models import Notification


ADMIN_NOTIFICATION_TOPICS = [
    {
        'key': 'utilizadores',
        'label': 'Utilizadores',
        'icon': 'bi-people',
        'description': 'Novos registos e entradas na base.',
        'title_markers': (
            'novo utilizador registado',
        ),
    },
    {
        'key': 'validacao',
        'label': 'Validacao',
        'icon': 'bi-patch-check',
        'description': 'Perfis que entraram em fila para aprovacao.',
        'title_markers': (
            'perfil pendente para validacao',
            'perfil pronto para validacao',
            'perfil pendente por idade minima',
        ),
    },
    {
        'key': 'contactos',
        'label': 'Contactos',
        'icon': 'bi-telephone',
        'description': 'Pedidos de contacto e respetiva fila.',
        'title_markers': (
            'novo pedido de contacto',
            'novos pedidos de contacto',
            'pedido de contacto',
        ),
    },
    {
        'key': 'colocacoes',
        'label': 'Colocacoes',
        'icon': 'bi-briefcase-fill',
        'description': 'Candidaturas aceites que contam como colocacao.',
        'title_markers': (
            'nova colocacao em emprego',
        ),
    },
]

DEFAULT_NOTIFICATION_TOPIC = {
    'key': 'geral',
    'label': 'Geral',
    'icon': 'bi-bell',
    'description': 'Outras notificacoes da conta.',
}


def get_notification_topic(notification):
    title = (getattr(notification, 'titulo', '') or '').strip().lower()

    for topic in ADMIN_NOTIFICATION_TOPICS:
        if any(marker in title for marker in topic['title_markers']):
            return {
                'key': topic['key'],
                'label': topic['label'],
                'icon': topic['icon'],
                'description': topic['description'],
            }

    return dict(DEFAULT_NOTIFICATION_TOPIC)


def build_notification_groups(notifications):
    ordered_notifications = sorted(
        notifications,
        key=lambda notification: (notification.created_at, notification.id),
        reverse=True,
    )
    groups = {}

    for notification in ordered_notifications:
        topic = get_notification_topic(notification)
        notification.topic_key = topic['key']
        notification.topic_label = topic['label']
        notification.topic_icon = topic['icon']
        notification.topic_description = topic['description']

        if topic['key'] not in groups:
            groups[topic['key']] = {
                'key': topic['key'],
                'label': topic['label'],
                'icon': topic['icon'],
                'description': topic['description'],
                'notifications': [],
                'count': 0,
                'unread_count': 0,
                'latest_created_at': notification.created_at,
                'latest_id': notification.id,
            }

        groups[topic['key']]['notifications'].append(notification)
        groups[topic['key']]['count'] += 1
        if not notification.lida:
            groups[topic['key']]['unread_count'] += 1
        if (
            notification.created_at,
            notification.id,
        ) > (
            groups[topic['key']]['latest_created_at'],
            groups[topic['key']]['latest_id'],
        ):
            groups[topic['key']]['latest_created_at'] = notification.created_at
            groups[topic['key']]['latest_id'] = notification.id

    ordered_groups = sorted(
        groups.values(),
        key=lambda group: (group['latest_created_at'], group['latest_id']),
        reverse=True,
    )
    for group in ordered_groups:
        group.pop('latest_created_at', None)
        group.pop('latest_id', None)
    return ordered_groups


def notify_admins(title, message, tipo='INFO', exclude_user_ids=None):
    """Create the same notification for all active admin users."""
    User = get_user_model()
    admin_qs = User.objects.filter(
        perfil=User.ProfileType.ADMIN,
        is_active=True,
    )

    if exclude_user_ids:
        if not isinstance(exclude_user_ids, (list, tuple, set)):
            exclude_user_ids = [exclude_user_ids]
        admin_qs = admin_qs.exclude(pk__in=list(exclude_user_ids))

    notifications = [
        Notification(user=admin, titulo=title, mensagem=message, tipo=tipo)
        for admin in admin_qs
    ]
    Notification.objects.bulk_create(notifications)
    return len(notifications)
