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

def age(): return FieldSpec('age','Âge','integer','Ex. 28','Âge en années (17–90 pour le modèle Education)',minimum=17,maximum=90)
def hours(): return FieldSpec('hours_per_week','Heures travaillées / semaine','integer','Ex. 40','Entre 1 et 99 heures (modèle Education)',minimum=1,maximum=99)
def gain(): return FieldSpec('capital_gain','Gains en capital (USD)','decimal','Ex. 0','Valeur déclarée en dollars américains',minimum=0)
def loss(): return FieldSpec('capital_loss','Pertes en capital (USD)','decimal','Ex. 0','Valeur déclarée en dollars américains',minimum=0)
def work(): return FieldSpec('workclass','Catégorie d’emploi','select', choices=WORKCLASS)
def job(): return FieldSpec('occupation','Profession','select', choices=OCCUPATION)
def edu(): return FieldSpec('education','Niveau d’études déclaré','select', choices=EDUCATION)
def marital(): return FieldSpec('marital_status','Situation familiale','select', choices=MARITAL)
def income(): return FieldSpec('income','Revenu annuel (catégorie UCI)','select',choices=INCOME)

# --- Module occupation (clustering) : champs propres au pipeline ---
OCC_MARITAL = (('Never-married','Célibataire'), ('Married-civ-spouse','Marié(e)'), ('Married-spouse-absent','Marié(e), conjoint absent'), ('Married-AF-spouse','Marié(e) à un militaire'), ('Divorced','Divorcé(e)'), ('Separated','Séparé(e)'), ('Widowed','Veuf / veuve'))
RELATIONSHIP = (('Husband','Époux'), ('Wife','Épouse'), ('Not-in-family','Hors famille'), ('Own-child','Enfant du foyer'), ('Unmarried','Non marié(e)'), ('Other-relative','Autre parent'))
SEX = (('Female','Femme'), ('Male','Homme'))

def edu_num(): return FieldSpec('education_num','Années d’études','integer','Ex. 10','Niveau d’éducation numérique, de 1 à 16 (ex. 9 = Bac, 13 = Licence)',minimum=1,maximum=16)
def occ_marital(): return FieldSpec('marital_status','Situation familiale','select', choices=OCC_MARITAL)
def relationship(): return FieldSpec('relationship','Rôle dans le foyer','select', choices=RELATIONSHIP)
def sex(): return FieldSpec('sex','Sexe','select', choices=SEX, help='Utilisé pour rapprocher les profils.')
MODULES = (
    ModuleSpec('income', 'Prédiction du revenu', 'Classification', 'Étudier la catégorie de revenu à partir du profil socio-professionnel.', 'income','Supervisé','wallet','violet','Membre 01', (age(), edu(), work(), job(), hours(), gain(), loss()), 'Choix de champs provisoire ; à aligner avec les features du modèle.'),
    ModuleSpec('occupation', 'Segmentation des profils', 'Clustering', 'Identifier des groupes de profils proches pour analyser la population active.', 'aucune (non supervisé)', 'Non supervisé','orbit','teal','Membre 02', (age(), edu_num(), hours(), work(), occ_marital(), job(), relationship(), sex(), income()), 'Le résultat décrit un profil type proche du vôtre, ce n’est pas une prédiction de profession.'),    
    ModuleSpec('age', 'Estimation de l’âge', 'Régression', 'Estimer l’âge à partir du contexte professionnel et personnel.', 'age','Supervisé','calendar','orange','Membre 03', (edu(), work(), job(), hours(), marital()), 'Le champ âge est volontairement absent : c’est la cible.'),
    ModuleSpec('hours', 'Temps de travail', 'Régression', 'Estimer le volume hebdomadaire de travail selon le profil.', 'hours-per-week','Supervisé','clock','blue','Membre 04', (age(), edu(), work(), job(), marital()), 'Le temps de travail est la variable cible et ne figure pas dans le formulaire.'),
    ModuleSpec('education', 'Niveau d’études', 'Classification binaire', 'Estimer niveau supérieur / niveau non supérieur pour suggérer une orientation initiale.', 'education (2 classes)','Supervisé','graduation','pink','Membre 05', (age(), hours(), gain(), loss(), work(), job(), income()), 'Formulaire compatible avec les sept variables brutes du pipeline XGBoost. Revenu : seuil historique américain en USD ; ce résultat ne vérifie aucun diplôme. À confirmer par l’utilisateur.'),
    ModuleSpec('workclass', 'Catégorie professionnelle', 'Classification', 'Estimer la catégorie d’emploi selon le profil socio-professionnel.', 'workclass','Supervisé','briefcase','lime','Membre 06', (age(), edu(), job(), hours(), marital()), 'Les caractéristiques sont provisoires : adapter au pipeline du membre 06.'),
)

BY_SLUG = {m.slug: m for m in MODULES}
assert len(BY_SLUG) == len(MODULES), 'Slug de module dupliqué'
