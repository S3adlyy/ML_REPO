"""Firebase credentials stay on the server; tokens are never persisted."""
from django.conf import settings


def verify_token(token):
    import firebase_admin
    from firebase_admin import auth
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(options={'projectId': settings.FIREBASE_CONFIG['projectId']})
    return auth.verify_id_token(token, app=app, check_revoked=True)
