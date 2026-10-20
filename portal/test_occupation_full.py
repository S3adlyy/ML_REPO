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
        with patch('portal.views.execute', return_value={'label': 'Jeunes célibataires', 'segment': '1', 'note': 'x'}):
            res = self.client.post(reverse('portal:occupation_profil'), data)
        self.assertContains(res, 'Votre groupe')
