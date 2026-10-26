import hashlib
import json
import logging
import time
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from .catalog import MODULES, INCOME_EDUCATION, WORKCLASS, OCCUPATION, INCOME
from .firebase import verify_token
from .models import MemberProfile, AnalysisRecord

log = logging.getLogger(__name__)

class OnboardingForm(forms.Form):
    interests = forms.MultipleChoiceField(label='Que souhaitez-vous explorer ?', choices=[(m.slug, m.title) for m in MODULES], widget=forms.CheckboxSelectMultiple)
    age = forms.IntegerField(label='Quel âge avez-vous ?', min_value=17, max_value=90)
    education = forms.ChoiceField(label='Quel est votre niveau d’études ?', choices=[('', 'Choisir un niveau'), *INCOME_EDUCATION])
    workclass = forms.ChoiceField(label='Dans quel secteur travaillez-vous ?', choices=[('', 'Choisir un secteur'), *WORKCLASS])
    occupation = forms.ChoiceField(label='Quelle est votre activité principale ?', choices=[('', 'Choisir une activité'), *OCCUPATION])
    hours_per_week = forms.IntegerField(label='Combien d’heures travaillez-vous par semaine ?', min_value=1, max_value=99)
    income = forms.ChoiceField(label='Votre tranche de revenu annuel (USD)', required=False, choices=[('', 'Je préfère compléter plus tard'), *INCOME])
    capital_gain = forms.DecimalField(label='Gains en capital annuels (USD)', required=False, min_value=0, max_value=99999)
    capital_loss = forms.DecimalField(label='Pertes en capital annuelles (USD)', required=False, min_value=0, max_value=4356)
    consent = forms.BooleanField(label='Enregistrer ces réponses dans mon profil pour préremplir mes analyses.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('interests', 'consent'):
                field.widget.attrs['class'] = 'input-control'
        for name in ('capital_gain', 'capital_loss'):
            self.fields[name].widget.attrs['placeholder'] = 'Facultatif · 0 si aucun'

@require_GET
def auth_page(request, mode='signin'):
    if request.user.is_authenticated:
        return redirect('portal:dashboard')
    return render(request, 'portal/auth.html', {'mode': mode, 'firebase_config': settings.FIREBASE_CONFIG, 'firebase_ready': settings.FIREBASE_SERVER_READY and all(settings.FIREBASE_CONFIG.values())})

@require_POST
def firebase_session(request):
    if not settings.FIREBASE_SERVER_READY or not all(settings.FIREBASE_CONFIG.values()):
        return JsonResponse({'error': 'La connexion sera disponible dès que Firebase sera configuré.'}, status=503)
    try:
        data = json.loads(request.body)
        token = data.get('idToken') if isinstance(data, dict) else None
        if not isinstance(token, str) or not token or len(token) > 20000:
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Requête de connexion invalide.'}, status=400)
    try:
        claims = verify_token(token)
        uid = claims['uid']
        if not isinstance(uid, str) or not uid or len(uid) > 128 or time.time() - claims.get('auth_time', 0) > 300:
            raise ValueError('Recent authentication required')
    except ImportError:
        return JsonResponse({'error': 'Le service de connexion doit être configuré.'}, status=503)
    except Exception:
        log.warning('Firebase sign-in verification failed')
        return JsonResponse({'error': 'Connexion non vérifiée. Reconnectez-vous et réessayez.'}, status=401)
    with transaction.atomic():
        user, created = get_user_model().objects.get_or_create(username='fb_' + hashlib.sha256(uid.encode()).hexdigest())
        if not user.is_active:
            return JsonResponse({'error': 'Ce compte est désactivé.'}, status=403)
        if created:
            user.set_unusable_password()
        user.email = str(claims.get('email', ''))[:254]
        user.first_name = str(claims.get('name', ''))[:150]
        user.save()
        profile, _ = MemberProfile.objects.get_or_create(user=user, defaults={'firebase_uid': uid})
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session.set_expiry(3600)
    from django.urls import reverse
    return JsonResponse({'redirect': reverse('portal:dashboard' if profile.completed else 'portal:onboarding')})

@require_POST
def signout(request):
    logout(request)
    return redirect('portal:home')

@login_required
def onboarding(request):
    profile = request.user.member_profile
    initial = {**profile.answers, 'interests': profile.interests, 'consent': profile.completed}
    form = OnboardingForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        profile.interests = form.cleaned_data['interests']
        profile.answers = {k: (float(v) if k in ('capital_gain', 'capital_loss') else v) for k, v in form.cleaned_data.items() if k not in ('interests', 'consent') and v is not None and v != ''}
        education_codes = {value: i+1 for i, (value, _) in enumerate(INCOME_EDUCATION)}
        profile.answers['education_num'] = education_codes[profile.answers['education']]
        profile.completed = True
        profile.save()
        messages.success(request, 'Votre profil est prêt. Choisissez votre première exploration.')
        return redirect('portal:dashboard')
    groups = [('Vos envies', 'Qu’aimeriez-vous mieux comprendre ?', 'Choisissez les sujets qui vous intéressent. Vous pourrez explorer les six modules à tout moment.', ['interests']), ('Votre parcours', 'Chaque parcours est unique.', 'Ces réponses préremplissent les champs compatibles de vos modèles.', ['age', 'education', 'workclass', 'occupation', 'hours_per_week']), ('Les derniers détails', 'Un peu de contexte. À votre rythme.', 'Les montants sont facultatifs et exprimés en dollars américains, comme dans les données des modèles.', ['income', 'capital_gain', 'capital_loss', 'consent'])]
    steps = [{'label': a, 'title': b, 'description': c, 'fields': [form[k] for k in d]} for a,b,c,d in groups]
    return render(request, 'portal/onboarding.html', {'form': form, 'steps': steps})

@login_required
@require_GET
def dashboard(request):
    from ml_modules.common import model_installed
    profile = request.user.member_profile
    return render(request, 'portal/dashboard.html', {
        'active': 'dashboard', 'profile': profile,
        'modules': [{'spec': m, 'installed': model_installed(m.slug), 'saved': m.slug in profile.interests} for m in MODULES],
        'recent': request.user.analyses.all()[:6], 'analysis_count': request.user.analyses.count(),
    })

def profile_initial(request, module):
    if not request.user.is_authenticated:
        return {}
    profile = MemberProfile.objects.filter(user=request.user).first()
    if not profile:
        return {}
    values = profile.answers
    return {f.key: values[f.key] for f in module.fields if f.key in values and (f.kind != 'select' or str(values[f.key]) in dict(f.choices))}

def record_analysis(request, module, result):
    if request.user.is_authenticated:
        AnalysisRecord.objects.create(user=request.user, module_slug=module.slug, module_title=module.title, label=result['label'][:500])

@login_required
@require_POST
def clear_history(request):
    request.user.analyses.all().delete()
    messages.success(request, 'Votre historique a été effacé.')
    return redirect('portal:dashboard')
