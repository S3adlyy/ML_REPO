"""Catalogue d'équipe : chaque membre édite UNIQUEMENT son entrée + son adapter.

Les champs des modules autres que education sont des exemples UI : à aligner sur le
pipeline entraîné (les variables cibles NE DOIVENT PAS figurer parmi les entrées).
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: str = 'integer'    # integer | decimal | select
    placeholder: str = ''
    help: str = ''
    choices: tuple = ()
    minimum: Optional[int] = None
    maximum: Optional[int] = None

@dataclass(frozen=True)
class ModuleSpec:
    slug: str
    title: str
    tag: str
    intro: str
    target: str
    method: str
    icon: str
    accent: str
    team: str
    fields: tuple
    note: str = ''

WORKCLASS = (('Private','Secteur privé'), ('Self-emp-not-inc','Indépendant'), ('Self-emp-inc','Indépendant (inc.)'), ('Federal-gov','Administration fédérale'), ('Local-gov','Administration locale'), ('State-gov','Administration régionale'), ('Without-pay','Sans rémunération'), ('Never-worked','Jamais travaillé'), ('Unknown','Non renseigné'))
OCCUPATION = (('Adm-clerical','Administration'), ('Exec-managerial','Direction / management'), ('Prof-specialty','Profession spécialisée'), ('Sales','Vente'), ('Craft-repair','Artisanat / réparation'), ('Other-service','Services'), ('Tech-support','Support technique'), ('Machine-op-inspct','Opération de machines'), ('Transport-moving','Transport / logistique'), ('Handlers-cleaners','Manutention / nettoyage'), ('Farming-fishing','Agriculture / pêche'), ('Protective-serv','Services de protection'), ('Priv-house-serv','Service domestique'), ('Armed-Forces','Forces armées'), ('Unknown','Non renseigné'))
EDUCATION = (('HS-grad','Bac / lycée'), ('Some-college','Études supérieures non diplômantes'), ('Bachelors','Licence'), ('Masters','Master'), ('Doctorate','Doctorat'), ('Assoc-voc','Diplôme intermédiaire professionnel'), ('Assoc-acdm','Diplôme intermédiaire académique'), ('11th','Avant le Bac'))
MARITAL = (('Never-married','Célibataire'), ('Married-civ-spouse','Marié(e)'), ('Divorced','Divorcé(e)'), ('Separated','Séparé(e)'), ('Widowed','Veuf / veuve'))
INCOME = (('<=50K','Jusqu’à 50 000 USD / an'), ('>50K','Plus de 50 000 USD / an'))
RELATIONSHIP = (
    ('Husband', 'Époux'),
    ('Wife', 'Épouse'),
    ('Not-in-family', 'Hors foyer familial'),
    ('Own-child', 'Enfant au foyer'),
    ('Unmarried', 'Célibataire / non marié(e)'),
    ('Other-relative', 'Autre parenté'),
)
NATIVE_US = (
    ('1', 'États-Unis (United-States)'),
    ('0', 'Autre pays d’origine'),
)

def age(): return FieldSpec('age','Âge','integer','Ex. 28','Âge en années (17–90)',minimum=17,maximum=90)
def hours(): return FieldSpec('hours_per_week','Heures travaillées / semaine','integer','Ex. 40','Entre 1 et 99 heures',minimum=1,maximum=99)
def gain(): return FieldSpec('capital_gain','Gains en capital (USD)','decimal','Ex. 0','Valeur déclarée en dollars américains',minimum=0)
def loss(): return FieldSpec('capital_loss','Pertes en capital (USD)','decimal','Ex. 0','Valeur déclarée en dollars américains',minimum=0)
def work(): return FieldSpec('workclass','Catégorie d’emploi','select', choices=WORKCLASS)
def job(): return FieldSpec('occupation','Profession','select', choices=OCCUPATION)
def edu(): return FieldSpec('education','Niveau d’études déclaré','select', choices=EDUCATION)
def marital(): return FieldSpec('marital_status','Situation familiale','select', choices=MARITAL)
def income(): return FieldSpec('income','Revenu annuel (catégorie UCI)','select',choices=INCOME)
def relationship(): return FieldSpec('relationship','Lien familial / foyer','select',choices=RELATIONSHIP)
def native_us(): return FieldSpec('native_us','Origine géographique','select',choices=NATIVE_US)

# --- Module income (Membre 01) : champs alignés sur le pipeline XGBoost ---------
# 8 variables brutes du modèle ; sex, race et marital-status volontairement absents.
INCOME_EDUCATION = (('Preschool','Maternelle / aucune scolarité'), ('1st-4th','Primaire (1re–4e)'), ('5th-6th','Primaire (5e–6e)'), ('7th-8th','Collège (7e–8e)'), ('9th','9e année'), ('10th','10e année'), ('11th','11e année'), ('12th','12e année sans diplôme'), ('HS-grad','Bac / lycée'), ('Some-college','Études supérieures non diplômantes'), ('Assoc-voc','Diplôme intermédiaire professionnel'), ('Assoc-acdm','Diplôme intermédiaire académique'), ('Bachelors','Licence'), ('Masters','Master'), ('Prof-school','École professionnelle (médecine, droit…)'), ('Doctorate','Doctorat'))
INCOME_RELATIONSHIP = (('Husband','Époux'), ('Wife','Épouse'), ('Own-child','Enfant du foyer'), ('Not-in-family','Hors famille (vit seul·e / colocation)'), ('Unmarried','Non marié(e), avec personnes à charge'), ('Other-relative','Autre membre de la famille'))

def income_fields():
    return (
        FieldSpec('age','Âge','integer','Ex. 38','Âge en années (17–90)',minimum=17,maximum=90),
        FieldSpec('education','Niveau d’études','select', choices=INCOME_EDUCATION),
        FieldSpec('workclass','Catégorie d’emploi','select', choices=WORKCLASS),
        FieldSpec('occupation','Profession','select', choices=OCCUPATION),
        FieldSpec('relationship','Rôle dans le foyer','select', help='Situation dans le foyer telle que déclarée au recensement', choices=INCOME_RELATIONSHIP),
        FieldSpec('hours_per_week','Heures travaillées / semaine','integer','Ex. 40','Entre 1 et 99 heures',minimum=1,maximum=99),
        FieldSpec('capital_gain','Gains en capital (USD)','decimal','Ex. 0','Entre 0 et 99 999 USD (plage des données)',minimum=0,maximum=99999),
        FieldSpec('capital_loss','Pertes en capital (USD)','decimal','Ex. 0','Entre 0 et 4 356 USD (plage des données)',minimum=0,maximum=4356),
    )
# --- Module occupation (clustering) : champs propres au profil ---
OCC_MARITAL = (('Never-married','Célibataire'), ('Married-civ-spouse','Marié(e)'), ('Married-spouse-absent','Marié(e), conjoint absent'), ('Married-AF-spouse','Marié(e) à un militaire'), ('Divorced','Divorcé(e)'), ('Separated','Séparé(e)'), ('Widowed','Veuf / veuve'))
OCC_RELATIONSHIP = (('Husband','Époux'), ('Wife','Épouse'), ('Not-in-family','Hors famille'), ('Own-child','Enfant du foyer'), ('Unmarried','Non marié(e)'), ('Other-relative','Autre parent'))
OCC_SEX = (('Female','Femme'), ('Male','Homme'))

def occ_edu_num(): return FieldSpec('education_num','Années d’études','integer','Ex. 10','Niveau d’éducation numérique, de 1 à 16 (ex. 9 = Bac, 13 = Licence)',minimum=1,maximum=16)
def occ_marital(): return FieldSpec('marital_status','Situation familiale','select', choices=OCC_MARITAL)
def occ_relationship(): return FieldSpec('relationship','Rôle dans le foyer','select', choices=OCC_RELATIONSHIP)
def occ_sex(): return FieldSpec('sex','Sexe','select', choices=OCC_SEX, help='Utilisé pour rapprocher les profils.')
MODULES = (
    ModuleSpec('income', 'Prédiction du revenu', 'Classification binaire', 'Estimer si une personne gagne plus de 50 000 USD par an à partir de son profil socio-professionnel.', 'income','Supervisé','wallet','violet','Membre 01', income_fields(), 'Pipeline XGBoost réglé (8 variables brutes, seuil issu de model_metadata.json). Sexe, origine et situation maritale ne sont pas utilisés. Données du recensement américain de 1994 : résultat indicatif, non décisionnel.'),
    ModuleSpec('occupation', 'Segmentation des profils', 'Clustering', 'Identifier des groupes de profils proches pour analyser la population active.', 'aucune (non supervisé)', 'Non supervisé','orbit','teal','Membre 02', (age(), occ_edu_num(), hours(), work(), occ_marital(), job(), occ_relationship(), occ_sex(), income()), 'Le résultat décrit un profil type proche du vôtre, ce n’est pas une prédiction de profession.'),
    ModuleSpec('has_capital', 'Propension au capital', 'Classification binaire', 'Estimer la probabilité qu’un individu dispose de revenus ou pertes de capital.', 'has_capital','Supervisé','spark','orange','Bilal El Eter (Membre 03)', (age(), edu(), work(), job(), hours(), marital(), relationship(), income(), native_us()), 'Modèle HistGradientBoosting avec pondération des classes. Fuite évitée : exclusion stricte de capital-gain et capital-loss. Seuil optimal calibré à 0.685.'),
    ModuleSpec('hours', 'Temps de travail', 'Régression', 'Estimer le volume hebdomadaire de travail selon le profil.', 'hours-per-week','Supervisé','clock','blue','Membre 04', (age(), edu(), work(), job(), marital()), 'Le temps de travail est la variable cible et ne figure pas dans le formulaire.'),
    ModuleSpec('education', 'Niveau d’études', 'Classification binaire', 'Estimer niveau supérieur / niveau non supérieur pour suggérer une orientation initiale.', 'education (2 classes)','Supervisé','graduation','pink','Membre 05', (age(), hours(), gain(), loss(), work(), job(), income()), 'Formulaire compatible avec les sept variables brutes du pipeline XGBoost. Revenu : seuil historique américain en USD ; ce résultat ne vérifie aucun diplôme. À confirmer par l’utilisateur.'),
    ModuleSpec('workclass', 'Catégorie professionnelle', 'Classification', 'Estimer la catégorie d’emploi selon le profil socio-professionnel.', 'workclass','Supervisé','briefcase','lime','Membre 06', (age(), edu(), job(), hours(), marital()), 'Les caractéristiques sont provisoires : adapter au pipeline du membre 06.'),
)


BY_SLUG = {m.slug: m for m in MODULES}
assert len(BY_SLUG) == len(MODULES), 'Slug de module dupliqué'
