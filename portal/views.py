import json
import logging
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from .catalog import MODULES, BY_SLUG
from .forms import create_profile_form
from ml_modules.common import ModelNotReady, model_installed

log = logging.getLogger(__name__)


def resolve_module(slug):
    try:
        return BY_SLUG[slug]
    except KeyError:
        raise Http404('Module inconnu')


def execute(module, cleaned_data):
    """Frontière stable : portal ne connaît pas les algorithmes des membres."""
    from importlib import import_module
    adapter = import_module(f'ml_modules.{module.slug}.adapter')
    result = adapter.predict(dict(cleaned_data))
    if not isinstance(result, dict) or not isinstance(result.get('label'), str):
        raise ValueError('Le module doit retourner un dict avec label: str')
    return result

@require_GET
def home(request):
    return render(request, 'portal/home.html', {
        'modules': [dict(spec=m, installed=model_installed(m.slug)) for m in MODULES],
        'active': 'home'
    })

def module_detail(request, slug):
    module = resolve_module(slug)
    form = create_profile_form(module, data=request.POST if request.method == 'POST' else None)
    result, warning = None, None
    if request.method == 'POST' and form.is_valid():
        try:
            result = execute(module, form.cleaned_data)
        except ModelNotReady as exc:
            warning = str(exc)
        except Exception:
            log.exception('Erreur de prédiction %s', module.slug)
            warning = 'Prédiction indisponible. Vérifiez le pipeline, les variables et les versions de dépendances.'
    return render(request, 'portal/module.html', {
        'module': module, 'form': form, 'result': result, 'warning': warning,
        'installed': model_installed(slug), 'active': slug,
    })

@require_POST
def predict_api(request, slug):
    module = resolve_module(slug)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            return JsonResponse({'error': 'Un objet JSON est requis.'}, status=400)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'JSON invalide.'}, status=400)
    form = create_profile_form(module, data=payload)
    if not form.is_valid():
        return JsonResponse({'error': 'Champs invalides.', 'fields': form.errors.get_json_data()}, status=400)
    try:
        result = execute(module, form.cleaned_data)
        return JsonResponse({'module': slug, 'result': result})
    except ModelNotReady as exc:
        return JsonResponse({'error': str(exc), 'status': 'not_ready'}, status=503)
    except Exception:
        log.exception('Erreur API de prédiction %s', slug)
        return JsonResponse({'error': 'Prédiction indisponible.'}, status=503)

@require_GET
def health(request):
    return JsonResponse({'status': 'ok', 'service': 'prisma-ml-portal', 'modules': len(MODULES)})
