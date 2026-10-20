import json
from unittest.mock import patch
from unittest import skipUnless
from django.test import TestCase, Client
from django.urls import reverse
from .catalog import MODULES, BY_SLUG
from .forms import create_profile_form
from ml_modules.common import ModelNotReady, model_installed

class PortalSmokeTests(TestCase):
    def test_homepage_loads_and_shows_six_modules(self):
        response = self.client.get(reverse('portal:home'))
        self.assertEqual(response.status_code, 200)
        for module in MODULES:
            self.assertContains(response, module.title)

    def test_each_module_page(self):
        for module in MODULES:
            with self.subTest(module=module.slug):
                response = self.client.get(reverse('portal:module', args=[module.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, module.title)

    def test_education_features_exclude_leakage(self):
        keys = {field.key for field in BY_SLUG['education'].fields}
        self.assertEqual(len(keys), 7)
        self.assertNotIn('education', keys)
        self.assertNotIn('education_num', keys)

    def test_other_modules_exclude_target(self):
        for module in MODULES:
            keys = {f.key for f in module.fields}
            self.assertNotIn(module.target, keys)
            if module.slug == 'age': self.assertNotIn('age', keys)
            if module.slug == 'has_capital':
                self.assertNotIn('has_capital', keys)
                self.assertNotIn('capital_gain', keys)
                self.assertNotIn('capital_loss', keys)
            if module.slug == 'hours': self.assertNotIn('hours_per_week', keys)
            if module.slug == 'workclass': self.assertNotIn('workclass', keys)
            if module.slug == 'income': self.assertNotIn('income', keys)
            if module.slug == 'occupation': pass  # occupation est une colonne d'entrée du pipeline de clustering, pas une cible

    def test_has_capital_features_and_no_leakage(self):
        keys = {field.key for field in BY_SLUG['has_capital'].fields}
        self.assertEqual(len(keys), 9)
        self.assertNotIn('has_capital', keys)
        self.assertNotIn('capital_gain', keys)
        self.assertNotIn('capital_loss', keys)
        self.assertIn('age', keys)
        self.assertIn('workclass', keys)
        self.assertIn('education', keys)
        self.assertIn('occupation', keys)
        self.assertIn('hours_per_week', keys)
        self.assertIn('marital_status', keys)
        self.assertIn('relationship', keys)
        self.assertIn('income', keys)
        self.assertIn('native_us', keys)


    def test_invalid_profile_does_not_call_model(self):
        with patch('portal.views.execute') as execute:
            res = self.client.post(reverse('portal:module', args=['education']), {'age': -4})
            self.assertEqual(res.status_code, 200)
            execute.assert_not_called()

    def test_unknown_module_is_404(self):
        self.assertEqual(self.client.get('/modules/unknown/').status_code, 404)

    def test_health(self):
        res = self.client.get(reverse('portal:health'))
        self.assertEqual(res.json()['modules'], 6)

    def test_api_invalid_json(self):
        url = reverse('portal:predict_api', args=['education'])
        res = self.client.post(url, data='{', content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_csrf_protects_api(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse('portal:predict_api', args=['education'])
        res = client.post(url, data='{}', content_type='application/json')
        self.assertEqual(res.status_code, 403)

    def test_api_without_model_is_503(self):
        url = reverse('portal:predict_api', args=['education'])
        payload = {'age':28,'hours_per_week':40,'capital_gain':0,'capital_loss':0,
                   'workclass':'Private','occupation':'Adm-clerical','income':'<=50K'}
        with patch('portal.views.execute', side_effect=ModelNotReady('Pas de modèle')):
            res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.json()['status'], 'not_ready')

    def test_api_successful_adapter_contract(self):
        url = reverse('portal:predict_api', args=['education'])
        payload = {'age':28,'hours_per_week':40,'capital_gain':0,'capital_loss':0,
                   'workclass':'Private','occupation':'Adm-clerical','income':'<=50K'}
        with patch('portal.views.execute', return_value={'label': 'Niveau supérieur', 'probability_superior': 0.6}):
            res = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['result']['label'], 'Niveau supérieur')


@skipUnless(model_installed('education'), 'Le modèle Education n’est pas présent dans le dépôt Git')
class RealEducationModelIntegrationTests(TestCase):
    """Test du modèle réel : s’exécute seulement avec le .joblib présent."""

    def test_real_model_on_web_form(self):
        payload = {'age': 28, 'hours_per_week': 40, 'capital_gain': 0,
                   'capital_loss': 0, 'workclass': 'Private',
                   'occupation': 'Adm-clerical', 'income': '<=50K'}
        response = self.client.post(reverse('portal:module', args=['education']), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Niveau supérieur')
        self.assertIsNotNone(response.context['result'])

    def test_real_model_on_json_api(self):
        payload = {'age': 28, 'hours_per_week': 40, 'capital_gain': 0,
                   'capital_loss': 0, 'workclass': 'Private',
                   'occupation': 'Adm-clerical', 'income': '<=50K'}
        response = self.client.post(
            reverse('portal:predict_api', args=['education']),
            data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()['result']
        self.assertEqual(result['label'], 'Niveau supérieur')
        self.assertAlmostEqual(result['probability_superior'], 0.5797, places=3)
        self.assertAlmostEqual(result['threshold'], 0.52)

    def test_education_form_rejects_out_of_training_range(self):
        payload = {'age': 16, 'hours_per_week': 40, 'capital_gain': 0,
                   'capital_loss': 0, 'workclass': 'Private',
                   'occupation': 'Adm-clerical', 'income': '<=50K'}
        response = self.client.post(reverse('portal:module', args=['education']), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['result'])


# --- Module income (Membre 01) -------------------------------------------------
INCOME_PROFILE = {'age': 45, 'education': 'Masters', 'workclass': 'Private',
                  'occupation': 'Exec-managerial', 'relationship': 'Husband',
                  'hours_per_week': 50, 'capital_gain': 0, 'capital_loss': 0}
INCOME_META = {'threshold': 0.63, 'label_mapping': {'0': '≤ 50 000 USD / an', '1': '> 50 000 USD / an'},
               'raw_expected_columns': ['age', 'education', 'workclass', 'occupation', 'relationship',
                                        'hours-per-week', 'capital-gain', 'capital-loss']}


class FakeIncomePipeline:
    """Faux pipeline : vérifie les colonnes reçues et renvoie une probabilité fixe."""
    classes_ = [0, 1]

    def __init__(self, proba):
        self.proba, self.columns = proba, None

    def predict_proba(self, x):
        self.columns = list(x.columns)
        import numpy as np
        return np.array([[1 - self.proba, self.proba]])


class IncomeModuleTests(TestCase):
    """Tests du module income : passent sans .joblib (CI GitHub)."""

    def test_income_form_matches_model_features(self):
        keys = [f.key for f in BY_SLUG['income'].fields]
        self.assertEqual(keys, ['age', 'education', 'workclass', 'occupation', 'relationship',
                                'hours_per_week', 'capital_gain', 'capital_loss'])
        for sensitive in ('sex', 'race', 'marital_status', 'income'):
            self.assertNotIn(sensitive, keys)

    def test_income_capital_limits(self):
        module = BY_SLUG['income']
        self.assertFalse(create_profile_form(module, data={**INCOME_PROFILE, 'capital_gain': 150000}).is_valid())
        self.assertFalse(create_profile_form(module, data={**INCOME_PROFILE, 'capital_loss': 5000}).is_valid())
        self.assertTrue(create_profile_form(module, data={**INCOME_PROFILE, 'capital_gain': 99999}).is_valid())

    def _predict(self, proba):
        from ml_modules.income import adapter
        fake = FakeIncomePipeline(proba)
        with patch.object(adapter, 'read_metadata', return_value=INCOME_META), \
             patch.object(adapter, 'load_pipeline', return_value=fake):
            return adapter.predict(dict(INCOME_PROFILE)), fake

    def test_adapter_above_threshold(self):
        result, fake = self._predict(0.90)
        self.assertEqual(result['label'], '> 50 000 USD / an')
        self.assertAlmostEqual(result['probability'], 0.90)
        self.assertEqual(fake.columns, INCOME_META['raw_expected_columns'])

    def test_adapter_below_threshold(self):
        result, _ = self._predict(0.40)
        self.assertEqual(result['label'], '≤ 50 000 USD / an')

    def test_adapter_rejects_out_of_range_age(self):
        from ml_modules.income.adapter import predict
        with self.assertRaises(ValueError):
            predict({**INCOME_PROFILE, 'age': 10})

    def test_income_page_without_model_shows_warning(self):
        with patch('portal.views.execute', side_effect=ModelNotReady('Pas de modèle')):
            res = self.client.post(reverse('portal:module', args=['income']), INCOME_PROFILE)
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.context['result'])
        self.assertEqual(res.context['warning'], 'Pas de modèle')


@skipUnless(model_installed('income'), 'Le modèle Income n’est pas présent (normal sur GitHub)')
class RealIncomeModelIntegrationTests(TestCase):
    """Test du vrai modèle : s’exécute seulement si ml_models/income/pipeline.joblib existe."""

    def test_real_model_high_and_low_profiles(self):
        high = self.client.post(reverse('portal:module', args=['income']), INCOME_PROFILE)
        self.assertEqual(high.context['result']['label'], '> 50 000 USD / an')
        low_profile = {**INCOME_PROFILE, 'age': 22, 'education': 'HS-grad', 'occupation': 'Other-service',
                       'relationship': 'Own-child', 'hours_per_week': 25}
        low = self.client.post(reverse('portal:module', args=['income']), low_profile)
        self.assertEqual(low.context['result']['label'], '≤ 50 000 USD / an')

    def test_real_model_on_json_api(self):
        res = self.client.post(reverse('portal:predict_api', args=['income']),
                               data=json.dumps(INCOME_PROFILE), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertGreater(res.json()['result']['probability'], 0.5)


@skipUnless(model_installed('has_capital'), 'Le modèle has_capital n’est pas présent dans le dépôt Git')
class RealHasCapitalModelIntegrationTests(TestCase):
    """Test du modèle has_capital réel : s’exécute seulement avec le .joblib présent."""

    def test_real_model_on_web_form(self):
        payload = {
            'age': 35, 'education': 'Bachelors', 'workclass': 'Private',
            'occupation': 'Exec-managerial', 'hours_per_week': 45,
            'marital_status': 'Married-civ-spouse', 'relationship': 'Husband',
            'income': '>50K', 'native_us': '1',
        }
        response = self.client.post(reverse('portal:module', args=['has_capital']), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['result'])
        self.assertIn('label', response.context['result'])

    def test_real_model_on_json_api(self):
        payload = {
            'age': 35, 'education': 'Bachelors', 'workclass': 'Private',
            'occupation': 'Exec-managerial', 'hours_per_week': 45,
            'marital_status': 'Married-civ-spouse', 'relationship': 'Husband',
            'income': '>50K', 'native_us': '1',
        }
        response = self.client.post(
            reverse('portal:predict_api', args=['has_capital']),
            data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()['result']
        self.assertIn('label', result)
        self.assertIn('probability_capital', result)
        self.assertAlmostEqual(result['threshold'], 0.685, places=2)

    def test_has_capital_form_rejects_out_of_training_range(self):
        payload = {
            'age': 10, 'education': 'Bachelors', 'workclass': 'Private',
            'occupation': 'Exec-managerial', 'hours_per_week': 45,
            'marital_status': 'Married-civ-spouse', 'relationship': 'Husband',
            'income': '>50K', 'native_us': '1',
        }
        response = self.client.post(reverse('portal:module', args=['has_capital']), payload)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['result'])



# ---------------------------------------------------------------------------
# Module hours (temps partiel) — tests sans .joblib : bundle synthétique en mémoire
# ---------------------------------------------------------------------------
def _fake_hours_bundle():
    """Bundle de même structure que celui exporté par le notebook (données aléatoires)."""
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    from xgboost import XGBClassifier
    categories = {
        'workclass': ['Never-worked', 'Private', 'Self-emp-inc', 'Unknown'],
        'marital-status': ['Divorced', 'Married-civ-spouse', 'Never-married'],
        'occupation': ['Adm-clerical', 'Exec-managerial', 'Unknown'],
    }
    continues = ['age', 'education-num', 'log_capital_gain', 'log_capital_loss']
    cols = continues + ['has_capital', 'native_us']
    for name, cats in categories.items():
        cols += [f'{name}_{c}' for c in cats[1:]]          # drop_first
    rng = np.random.default_rng(0)
    x = pd.DataFrame(rng.random((200, len(cols))), columns=cols)
    y = (x['age'] > 0.5).astype(int)
    scaler = StandardScaler().fit(x[continues])
    x[continues] = scaler.transform(x[continues])
    model = XGBClassifier(n_estimators=5, max_depth=2).fit(x, y)
    return {'modele': model, 'scaler': scaler, 'colonnes': cols, 'continues': continues,
            'seuil': 0.26, 'categories': categories}


HOURS_PAYLOAD = {'age': 28, 'education': 'Bachelors', 'workclass': 'Private',
                 'occupation': 'Adm-clerical', 'marital_status': 'Never-married',
                 'capital_gain': 0, 'capital_loss': 0, 'native_us': '1'}


class HoursModuleTests(TestCase):
    def test_form_fields_exclude_target_and_sensitive(self):
        keys = {f.key for f in BY_SLUG['hours'].fields}
        self.assertEqual(keys, {'age', 'education', 'workclass', 'occupation', 'marital_status',
                                'capital_gain', 'capital_loss', 'native_us'})
        for banned in ('hours_per_week', 'sex', 'race', 'relationship', 'income'):
            self.assertNotIn(banned, keys)

    def test_adapter_contract_with_synthetic_bundle(self):
        from ml_modules.hours import adapter
        with patch.object(adapter, 'load_pipeline', return_value=_fake_hours_bundle()):
            out = adapter.predict(dict(HOURS_PAYLOAD))
        self.assertIsInstance(out['label'], str)
        self.assertTrue(0.0 <= out['probability_part_time'] <= 1.0)
        self.assertEqual(out['threshold'], 0.26)

    def test_row_matches_notebook_preprocessing(self):
        from ml_modules.hours import adapter
        bundle = _fake_hours_bundle()
        values = adapter.normalize_profile(dict(HOURS_PAYLOAD, capital_gain=1000))
        self.assertEqual(values['has_capital'], 1)
        self.assertEqual(values['education-num'], 13)
        row = adapter.build_row(values, bundle)
        self.assertEqual(list(row.columns), bundle['colonnes'])
        self.assertEqual(row.at[0, 'workclass_Private'], 1)
        self.assertEqual(row.at[0, 'occupation_Exec-managerial'], 0)

    def test_unknown_category_rejected(self):
        from ml_modules.hours import adapter
        with patch.object(adapter, 'load_pipeline', return_value=_fake_hours_bundle()):
            with self.assertRaises(ValueError):
                adapter.predict(dict(HOURS_PAYLOAD, occupation='Astronaut'))

    def test_wrong_artifact_format_is_not_ready(self):
        from ml_modules.hours import adapter
        with patch.object(adapter, 'load_pipeline', return_value=object()):
            with self.assertRaises(ModelNotReady):
                adapter.predict(dict(HOURS_PAYLOAD))

    def test_web_form_with_synthetic_bundle(self):
        from ml_modules.hours import adapter
        with patch.object(adapter, 'load_pipeline', return_value=_fake_hours_bundle()):
            res = self.client.post(reverse('portal:module', args=['hours']), HOURS_PAYLOAD)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Résultat estimé')

    def test_form_rejects_out_of_range_age(self):
        with patch('portal.views.execute') as execute:
            res = self.client.post(reverse('portal:module', args=['hours']), dict(HOURS_PAYLOAD, age=12))
            self.assertEqual(res.status_code, 200)
            execute.assert_not_called()


@skipUnless(model_installed('hours'), 'Le modèle hours n’est pas présent dans le dépôt Git')
class RealHoursModelIntegrationTests(TestCase):
    """S'exécute seulement en local, avec ml_models/hours/pipeline.joblib."""

    def test_real_model_on_web_form(self):
        res = self.client.post(reverse('portal:module', args=['hours']), HOURS_PAYLOAD)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Résultat estimé')

    def test_real_model_on_json_api(self):
        res = self.client.post(reverse('portal:predict_api', args=['hours']),
                               data=json.dumps(HOURS_PAYLOAD), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('probability_part_time', res.json()['result'])


class HoursResultDisplayTests(TestCase):
    """Probabilité, priorité et facteurs : bundle synthétique, aucun .joblib requis."""

    def _predict(self, **overrides):
        from ml_modules.hours import adapter
        with patch.object(adapter, 'load_pipeline', return_value=_fake_hours_bundle()):
            return adapter.predict(dict(HOURS_PAYLOAD, **overrides))

    def test_result_shows_percentage_for_template(self):
        out = self._predict()
        self.assertEqual(out['value'], round(out['probability_part_time'] * 100, 1))
        self.assertIn('probabilité', out['unit'])

    def test_priority_tier_is_consistent_with_probability(self):
        from ml_modules.hours import adapter
        out = self._predict()
        p = out['probability_part_time']
        expected = 'high' if p >= adapter.HIGH_PROBA else ('medium' if p >= out['threshold'] else 'low')
        self.assertEqual(out['priority'], expected)
        self.assertEqual(out['label'], adapter.TIERS[expected][0])

    def test_factors_are_listed_in_note(self):
        out = self._predict()
        self.assertLessEqual(len(out['factors']), 3)
        for factor in out['factors']:
            self.assertIn(factor, out['note'])

    def test_hours_form_has_help_text_on_every_field(self):
        for field in BY_SLUG['hours'].fields:
            self.assertTrue(field.help, field.key)
