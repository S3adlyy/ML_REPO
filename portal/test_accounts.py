import json
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from .models import MemberProfile, AnalysisRecord

CONFIG = {'apiKey': 'test', 'authDomain': 'test.firebaseapp.com', 'projectId': 'test', 'appId': 'test'}

@override_settings(FIREBASE_CONFIG=CONFIG, FIREBASE_SERVER_READY=True)
class AccountFlowTests(TestCase):
    def claims(self, uid='test-user'):
        return {'uid': uid, 'email': 'sample@example.com', 'name': 'Sam', 'auth_time': time.time()}

    def sign_in(self, claims=None):
        with patch('portal.accounts.verify_token', return_value=claims or self.claims()):
            return self.client.post('/auth/session/', json.dumps({'idToken': 'test-token'}), content_type='application/json')

    def test_verified_account_is_created_and_sent_to_onboarding(self):
        response = self.sign_in()
        self.assertEqual(response.json()['redirect'], '/onboarding/')
        user = get_user_model().objects.get()
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.member_profile.firebase_uid, 'test-user')
        self.assertEqual(self.client.get('/workspace/').status_code, 200)
        self.assertEqual(self.client.get('/onboarding/').status_code, 200)

    def test_invalid_token_cannot_create_account(self):
        with patch('portal.accounts.verify_token', side_effect=ValueError):
            response = self.client.post('/auth/session/', json.dumps({'idToken': 'bad'}), content_type='application/json')
        self.assertEqual(response.status_code, 401)
        self.assertFalse(get_user_model().objects.exists())

    def test_stale_login_is_rejected(self):
        claims = self.claims(); claims['auth_time'] -= 600
        self.assertEqual(self.sign_in(claims).status_code, 401)
        self.assertFalse(get_user_model().objects.exists())

    def test_invalid_payloads(self):
        for payload in ['null', '[]', '{}', '{', '{"idToken": 3}']:
            self.assertEqual(self.client.post('/auth/session/', payload, content_type='application/json').status_code, 400)

    def test_csrf_required_for_login_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/auth/session/', '{}', content_type='application/json').status_code, 403)
        self.assertEqual(client.post('/signout/').status_code, 403)
        self.assertEqual(self.client.get('/signout/').status_code, 405)

    def test_profiles_are_not_linked_by_unverified_email(self):
        first = self.sign_in(); self.assertEqual(first.status_code, 200)
        self.client.post('/signout/')
        self.sign_in(self.claims('second-user'))
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_profile_validation_prefill_and_target_exclusion(self):
        self.sign_in()
        payload = {'interests': ['income', 'education'], 'age': 28, 'education': 'Bachelors', 'workclass': 'Private', 'occupation': 'Sales', 'hours_per_week': 40, 'consent': 'on'}
        bad = self.client.post('/onboarding/', {**payload, 'age': 120})
        self.assertEqual(bad.status_code, 200)
        self.assertFalse(MemberProfile.objects.get().completed)
        response = self.client.post('/onboarding/', payload)
        self.assertRedirects(response, '/workspace/')
        profile = MemberProfile.objects.get()
        self.assertEqual(profile.answers['education_num'], 13)
        self.assertNotIn('capital_gain', profile.answers)
        self.assertNotIn('race', profile.answers)
        income_form = self.client.get('/modules/income/').context['form']
        self.assertEqual(income_form.initial['age'], 28)
        self.assertNotIn('income', income_form.initial)
        hours_form = self.client.get('/modules/hours/').context['form']
        self.assertNotIn('hours_per_week', hours_form.initial)
        education_form = self.client.get('/modules/education/').context['form']
        self.assertNotIn('education', education_form.initial)

    def test_personal_history_does_not_expose_other_users(self):
        self.sign_in()
        first = get_user_model().objects.get()
        AnalysisRecord.objects.create(user=first, module_slug='income', module_title='Income', label='PRIVATE-FIRST-RESULT')
        self.client.post('/signout/')
        self.sign_in(self.claims('second-user'))
        self.assertNotContains(self.client.get('/workspace/'), 'PRIVATE-FIRST-RESULT')
        self.client.post('/workspace/history/clear/')
        self.assertEqual(AnalysisRecord.objects.filter(user=first).count(), 1)

    def test_logged_in_prediction_saves_result_only(self):
        self.sign_in()
        payload = {'age':28,'hours_per_week':40,'capital_gain':0,'capital_loss':0,'workclass':'Private','occupation':'Sales','income':'<=50K'}
        with patch('portal.views.execute', return_value={'label': 'Example result'}):
            self.client.post('/modules/education/', payload)
        record = AnalysisRecord.objects.get()
        self.assertEqual(record.label, 'Example result')
        self.assertEqual(record.user.member_profile.firebase_uid, 'test-user')

    def test_private_pages_require_authentication(self):
        for path in ['/workspace/', '/onboarding/']:
            self.assertEqual(self.client.get(path).status_code, 302)

    @override_settings(FIREBASE_CONFIG={})
    def test_missing_config_is_unavailable(self):
        with override_settings(FIREBASE_CONFIG={'apiKey': '', 'authDomain': '', 'projectId': '', 'appId': ''}):
            self.assertEqual(self.client.post('/auth/session/', '{}', content_type='application/json').status_code, 503)
            self.assertContains(self.client.get('/signup/'), 'Firebase sera configuré')
