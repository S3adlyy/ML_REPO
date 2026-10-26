from django.test import TestCase
from django.urls import reverse

from .occupation_full import PROFILES


class OccupationTabsTests(TestCase):
    def test_dashboard_is_first_page_without_form(self):
        res = self.client.get(reverse('portal:module', args=['occupation']))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Vue d’ensemble')
        for mot in ('K-Means', 'K-Prototypes', 'ilhouette', 'Cramér'):
            self.assertNotContains(res, mot)
        self.assertAlmostEqual(sum(p['size'] for p in PROFILES), 100, delta=0.2)

    def test_profile_tab_has_form(self):
        res = self.client.get(reverse('portal:occupation_profil'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '<form')
        self.assertContains(res, 'Trouver mon groupe')

    def test_profile_post_highlights_group(self):
        from unittest.mock import patch
        data = dict(age=29, education_num=10, hours_per_week=40, workclass='Private', marital_status='Never-married',
                    occupation='Sales', relationship='Not-in-family', sex='Female', income='<=50K')
        from ml_modules.occupation.recommandations import recommander
        reco = recommander('1', data)
        with patch('portal.views.execute', return_value={'label': 'Les Nouveaux Départs', 'segment': '1', 'note': 'x', 'reco': reco}):
            res = self.client.post(reverse('portal:occupation_profil'), data)
        self.assertContains(res, 'Votre profil')
        self.assertContains(res, 'RECOMMANDATIONS')
        self.assertContains(res, 'Les Nouveaux Départs')
        self.assertContains(res, 'Investir tôt dans une formation')


class RecommandationsTests(TestCase):
    def test_every_group_has_three_pistes_and_no_gender_advice(self):
        from ml_modules.occupation.recommandations import GROUPES, recommander
        base = dict(age=30, education_num=9, hours_per_week=40, sex='Female')
        for seg in GROUPES:
            r = recommander(seg, base)
            self.assertEqual(len(r['pistes']), 3)
            texte = ' '.join(p['titre'] + p['texte'] for p in r['pistes']).lower()
            for mot in ('femme', 'homme', 'sexe'):
                self.assertNotIn(mot, texte)

    def test_gap_depends_on_education(self):
        from ml_modules.occupation.recommandations import recommander
        bas = recommander('1', dict(age=25, education_num=8, hours_per_week=35))['ecart']
        haut = recommander('1', dict(age=25, education_num=13, hours_per_week=35))['ecart']
        self.assertIn('il vous manque', bas)
        self.assertIn('atteint déjà', haut)
