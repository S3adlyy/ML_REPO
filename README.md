# livrable_orentation — Application Django + 6 modules Machine Learning

> Projet d'équipe Adult / UCI, **prêt à lancer en local avec ton vrai modèle `education`**.
> **Deux distributions :** l’archive de démonstration inclut le pipeline Education pour les tests locaux ; l’archive « Code GitHub sans modèles » contient uniquement le code et la documentation. Après un `git clone`, chaque membre fournit ses artefacts ML séparément.

## 1. Ce qu'il y a dans ce dossier

- `manage.py` : commandes Django (serveur, migration, tests).
- `config/` : réglages Django, URLs principales, serveur WSGI / ASGI.
- `portal/` : interface commune, formulaires, vues, routes et tests.
- `templates/portal/` : pages HTML (accueil, modules, structure commune).
- `static/portal/` : styles CSS responsive, JavaScript (navigation/recherche).
- `ml_modules/common.py` : chargeur des pipelines et helpers communs.
- `ml_modules/education/adapter.py` : **connexion directe** entre formulaire Django et modèle XGBoost.
- `ml_modules/{income,occupation,age,hours,workclass}/adapter.py` : points de branchement réservés aux autres membres.
- `ml_models/education/pipeline.joblib` : le **modèle réel entraîné**, présent dans le ZIP de démonstration mais absent de l’archive source GitHub et des clones.
- `ml_models/education/model_metadata.json` : features attendues, classes et seuil **0.52**.
- `scripts/doctor_model.py` : vérifie le modèle et produit une prédiction, même sans Django.
- `requirements.txt` : dépendances et versions nécessaires.
- `.github/workflows/django-ci.yml` : vérification automatique des Pull Requests.

### Arborescence

```text
livrable_orentation/
├── manage.py
├── requirements.txt
├── .gitignore
├── .env.example
├── README.md
├── CONTRIBUTING.md
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── portal/
│   ├── catalog.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   └── context_processors.py
├── ml_modules/
│   ├── common.py
│   ├── education/adapter.py
│   ├── income/adapter.py
│   ├── occupation/adapter.py
│   ├── age/adapter.py
│   ├── hours/adapter.py
│   └── workclass/adapter.py
├── ml_models/
│   ├── education/
│   │   ├── pipeline.joblib      # optionnel : LOCAL uniquement
│   │   ├── model_metadata.json
│   │   └── exemple_profil.json
│   ├── income/
│   ├── occupation/
│   ├── age/
│   ├── hours/
│   └── workclass/
├── templates/portal/
│   ├── base.html
│   ├── home.html
│   └── module.html
├── static/portal/
│   ├── css/app.css
│   └── js/app.js
└── scripts/doctor_model.py
```

## 2. Lancer l'application sur macOS (M1 ou Intel)

Prérequis : **Python 3.13**, Terminal et accès à Internet pour installer les dépendances. Installer Python 3.13 s'il manque.

**Option rapide :** après décompression, entre `cd livrable_orentation && bash scripts/start_mac.sh` (installation, vérifications et démarrage automatiques).

**Option étape par étape dans Terminal :**

```bash
cd livrable_orentation
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Dans la **version de démonstration**, vérifie ton modèle, **avant même de démarrer Django** (dans la version « GitHub sans modèles », cette commande nécessite d’abord une copie privée de `pipeline.joblib`) :

```bash
python scripts/doctor_model.py
```

Résultat de l’exemple vérifié **avec le modèle Education local** : **Niveau supérieur**, score de classe supérieure **0.5797**, seuil **0.52**.

Puis lance le site :

```bash
python manage.py check
python manage.py migrate
python manage.py test
python manage.py runserver
```

Ouvre dans le navigateur :

- Accueil : **http://127.0.0.1:8000/**
- Ton modèle Education : **http://127.0.0.1:8000/modules/education/**
- État des modules : **http://127.0.0.1:8000/health/**

Pour arrêter : **Ctrl+C** dans Terminal. Pour reprendre plus tard : `source .venv/bin/activate && python manage.py runserver`.

### Sous Windows (PowerShell)

```powershell
cd livrable_orentation
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/doctor_model.py
python manage.py migrate
python manage.py test
python manage.py runserver
```

## 3. Tester une prédiction dans le navigateur

Ouvre `/modules/education/`, remplis ces champs :

| Champ affiché | Valeur exemple | Colonne ML |
|---|---|---|
| Âge | `28` | `age` |
| Heures travaillées / semaine | `40` | `hours-per-week` |
| Gains en capital | `0` | `capital-gain` |
| Pertes en capital | `0` | `capital-loss` |
| Catégorie d'emploi | `Secteur privé` (= `Private`) | `workclass` |
| Profession | `Administration` (= `Adm-clerical`) | `occupation` |
| Revenu annuel (catégorie UCI) | `Jusqu’à 50 000 USD/an` (= `<=50K`) | `income` |

Clique sur « Lancer l’analyse ». **Si** le pipeline Education approuvé est installé localement, le résultat s’affiche sur la droite. L’étiquette et le score proviennent **du vrai modèle**, pas d’une réponse simulée. Sans artefact local, le module affiche un état « non connecté ».

**Note métier :** la catégorie de revenu `<=50K` / `>50K` vient du recensement américain Adult, pas du contexte salarial tunisien. Ce résultat est expérimental et ne doit **jamais remplacer le diplôme déclaré/confirmé** par la personne.

## 4. Ce qui relie Django au modèle

```text
Navigateur / formulaire
         ↓
portal/urls.py → portal/views.py
         ↓ validation
portal/forms.py + portal/catalog.py
         ↓
ml_modules/education/adapter.py
         ↓
ml_modules/common.py (load_pipeline)
         ↓
ml_models/education/pipeline.joblib + model_metadata.json
         ↓
Résultat sur templates/portal/module.html
```

Le modèle attend **7 variables brutes** : `age`, `hours-per-week`, `capital-gain`, `capital-loss`, `workclass`, `occupation`, `income`.

Le pipeline `.joblib` contient **déjà** les étapes d'imputation, transformation log1p, encodage One-Hot et XGBoost. **Ne refais pas l'encodage dans la vue Django.** Le dossier `ml_models` doit rester privé : il ne doit pas être placé dans `static` ou exposé par une URL.

## 5. Tester l'API JSON

Endpoint : `POST /api/modules/education/predict/`

Exemple JSON attendu :

```json
{
  "age": 28,
  "hours_per_week": 40,
  "capital_gain": 0,
  "capital_loss": 0,
  "workclass": "Private",
  "occupation": "Adm-clerical",
  "income": "<=50K"
}
```

L'API utilise **la protection CSRF Django**. Pour un test simple via le navigateur, le formulaire HTML suffit. Pour une requête AJAX ou `curl`, récupère un jeton CSRF valide et envoie `X-CSRFToken` avec les cookies de la session. Ne supprime pas la protection CSRF juste pour le test. Les tests automatisés Django couvrent la route JSON.

## 6. Travail en équipe : intégrer chaque modèle sans le publier sur GitHub

**Objectif :** les six membres utilisent la **même application Django et le même dépôt GitHub**. Chaque membre entraîne son modèle séparément, le teste localement, puis pousse **uniquement le code d'intégration**, les tests et les fichiers de documentation (aucun modèle `.joblib`, aucun CSV, aucun secret).

### 6.1. Qui travaille sur quel dossier ?

| Module (`slug`) | Mission | Code ML à modifier | Fichier local du modèle (non publié) |
|---|---|---|---|
| `income` | Classification du revenu | `ml_modules/income/adapter.py` | `ml_models/income/pipeline.joblib` |
| `occupation` | Clustering de profils | `ml_modules/occupation/adapter.py` | `ml_models/occupation/pipeline.joblib` |
| `age` | Régression de l'âge | `ml_modules/age/adapter.py` | `ml_models/age/pipeline.joblib` |
| `hours` | Régression des heures travaillées | `ml_modules/hours/adapter.py` | `ml_models/hours/pipeline.joblib` |
| `education` | Classification du niveau d'études | `ml_modules/education/adapter.py` | `ml_models/education/pipeline.joblib` |
| `workclass` | Classification de la catégorie d'emploi | `ml_modules/workclass/adapter.py` | `ml_models/workclass/pipeline.joblib` |

La partie web commune est dans `portal/`, `templates/` et `static/` : **ne pas créer un deuxième projet Django**, ni modifier `portal/views.py` pour brancher individuellement un modèle. La vue commune choisit déjà le bon adaptateur suivant le module ouvert.

Les **champs de formulaire** sont définis dans `portal/catalog.py`, et `portal/forms.py` génère le formulaire automatiquement. Pour un modèle donné, modifier **uniquement l'entrée du `ModuleSpec` correspondant** (et, si nécessaire, les choix disponibles). Les listes de caractéristiques des cinq modules autres qu'`education` sont **provisoires** et doivent être vérifiées contre chaque modèle entraîné.

### 6.2. Étape A — Chaque membre clone le dépôt et crée sa branche

Une seule personne a déjà créé le repository et poussé le squelette. Pour chaque autre membre :

```bash
# Remplacer ORGANISATION_OU_COMPTE par le vrai propriétaire du dépôt.
git clone https://github.com/ORGANISATION_OU_COMPTE/livrable_orentation.git
cd livrable_orentation

# Toujours repartir de la version partagée.
git switch main
git pull --ff-only origin main

# Exemple pour le membre qui estime l'âge :
git switch -c feature/age
```

Branches suggérées : `feature/income`, `feature/occupation`, `feature/age`, `feature/hours`, `feature/education`, `feature/workclass`. **Une personne = une branche de fonctionnalité (et une Pull Request).** Personne ne pousse directement ses modifications sur `main` ; la fusion se fait après vérification. Si l'équipe utilise une branche `develop`, choisissez-la comme base et destination de façon cohérente.

### 6.3. Étape B — Installer le projet localement

```bash
# Depuis la racine du dépôt
python3.13 -m venv .venv
source .venv/bin/activate         # macOS / Linux
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py test
```

Sous Windows PowerShell, remplacer l'activation par `.venv\Scripts\Activate.ps1`. Sur macOS, si XGBoost signale `Library not loaded: @rpath/libomp.dylib`, installer **Homebrew OpenMP** : `brew install libomp`.

Le fichier `requirements.txt` actuel contient les versions utilisées pour recharger le **modèle Education** (Python 3.13, scikit-learn 1.8.0, XGBoost 3.1.3, etc.). **Chaque membre vérifie la compatibilité de son propre modèle avec ces versions** ; ne pas mettre à jour une dépendance partagée au hasard. Si un autre algorithme nécessite un paquet supplémentaire, le discuter dans la Pull Request et ajouter une version testée. Si deux pipelines réclament des versions réellement incompatibles, prévoir une isolation de l'inférence par service séparé plutôt que casser les autres modules.

### 6.4. Étape C — Exporter son pipeline ML complet et le placer seulement en local

Le travail d'entraînement a lieu dans le notebook du membre (hors application web). À la fin, il faut sauvegarder **les transformations apprises et l'algorithme dans le même pipeline**, lorsque la solution le permet.

Exemple pédagogique scikit-learn (à exécuter **après** avoir entraîné et validé son propre `pipeline` dans son notebook) :

```python
import joblib
joblib.dump(pipeline, 'pipeline.joblib')  # "pipeline" = objet déjà entraîné
```

Puis, **uniquement sur sa machine**, placer le fichier ici (exemple : âge) :

```text
ml_models/age/pipeline.joblib
```

Pour Education, le ZIP de démonstration comprenait déjà `ml_models/education/pipeline.joblib` et `model_metadata.json`. Sur un clone GitHub frais, **ce modèle n'est pas présent** : le copier depuis un canal privé approuvé avant de tester les prédictions réelles. Les autres membres utilisent chacun leur répertoire.

Si un modèle requiert un mapping de classes, un seuil ou une version de dépendance particulière, documenter ces valeurs dans son module (ou dans des métadonnées texte sans données personnelles). **Ne jamais inventer la liste des variables attendues : la relever du pipeline/notebook de la personne concernée.**

**Important :** `joblib.load()` peut exécuter du code provenant de l'artefact. Charger uniquement des modèles créés ou validés par l'équipe et reçus par un canal de confiance. Ne pas stocker les modèles dans `static/` ni dans un dossier public.

### 6.5. Étape D — Adapter son formulaire (seulement son module)

Dans `portal/catalog.py`, chaque module apparaît comme un `ModuleSpec(...)`. Le champ `fields=(...)` détermine ce que l'utilisateur saisit.

Exemple **réel du squelette** pour le module `age` :

```python
ModuleSpec(
    'age', 'Estimation de l’âge', 'Régression',
    'Estimer l’âge à partir du contexte professionnel et personnel.',
    'age', 'Supervisé', 'calendar', 'orange', 'Membre 03',
    (edu(), work(), job(), hours(), marital()),
    'Le champ âge est volontairement absent : c’est la cible.'
)
```

Cet exemple est une **configuration de départ**, pas la preuve que ces cinq entrées sont celles du modèle final du membre 3. Il faudra ajouter/supprimer les champs selon les colonnes réellement fournies à `fit()`. La **variable cible ne doit pas être utilisée comme caractéristique prédictive** (ex. ne pas demander `age` pour estimer `age`). Les valeurs de `<select>` doivent reprendre exactement les catégories apprises par le pipeline : les textes affichés à l'écran peuvent être traduits en français, les valeurs techniques non.

### 6.6. Étape E — Brancher le pipeline à Django avec son adaptateur

Le fichier `ml_modules/<slug>/adapter.py` expose cette interface commune :

```python
# profil : données déjà validées par le formulaire Django
# sortie : dictionnaire JSON-sérialisable, avec au minimum 'label' (str)
def predict(profile: dict) -> dict:
    return {'label': 'Résultat', 'note': 'Estimation indicative.'}
```

Le projet fournit déjà dans `ml_modules/common.py` :

- `load_pipeline(slug)` : charge `ml_models/<slug>/pipeline.joblib` (avec cache).
- `sample_frame(profile, mapping)` : convertit le formulaire en DataFrame d'une ligne.
- `predict_generic(...)` : aide pour classification, régression et clustering **si le pipeline accepte déjà les caractéristiques brutes du formulaire**.

Exemple **déjà présent** dans `ml_modules/age/adapter.py` (à adapter si son vrai pipeline exige d'autres caractéristiques) :

```python
from ml_modules.common import predict_generic


def predict(profile):
    return predict_generic(
        'age', profile, kind='regression',
        mapping={'hours_per_week': 'hours-per-week',
                 'marital_status': 'marital-status'},
        labels=None,
    )
```

`mapping` convertit les noms Python du formulaire en noms de colonnes d'entraînement ; par exemple `hours_per_week` devient `hours-per-week`. Pour une régression, `predict_generic` renvoie notamment un `label` et une `value` numérique ; pour un clustering, un `segment` ; pour une classification, un `label` correspondant à la catégorie prédite.

Si `predict_generic` ne convient pas, le membre écrit son propre `predict(profile)` dans **son** adaptateur, en utilisant le pipeline entraîné. Convertir les valeurs NumPy en types Python avant de renvoyer un dictionnaire JSON. Ne pas réentraîner le modèle dans une vue Django et ne pas refaire un encodage déjà présent dans le pipeline.

### 6.7. Étape F — Tester son modèle et l'application avant chaque push

**Vérification commune, sans modèle obligatoire :**

```bash
python manage.py check
python manage.py test
python manage.py runserver
```

La page de chaque membre se trouve à `http://127.0.0.1:8000/modules/<slug>/` et son API à `POST /api/modules/<slug>/predict/`. Le formulaire web permet de tester sans gérer manuellement un jeton CSRF. L'API exige la protection CSRF Django.

**Test réel local de son pipeline** : depuis la racine du dépôt, appeler son adaptateur avec un profil **dont les valeurs sont cohérentes avec son modèle**. Exemple de structure à adapter :

```python
from ml_modules.age.adapter import predict

profil_de_test = {
    # À remplacer par les clés et valeurs réelles du formulaire du membre
}
# predict(profil_de_test)  # décommenter après remplissage
```

Ne pas présenter un exemple fictif comme un résultat mesuré. Pour le modèle Education fourni, le test existant est directement exécutable : `python scripts/doctor_model.py`.

**Tests à compléter par chaque membre :** formulaire avec données valides, rejet de données invalides, appel de l'adaptateur, prédiction réelle avec le pipeline local et gestion du modèle absent. Ajouter des tests au projet sans rendre la CI dépendante d'un modèle ignoré par Git (mock des prédictions ou test d'intégration conditionnel). Les tests web génériques existent dans `portal/tests.py` ; les tests réels du module Education s'exécutent seulement si le `.joblib` local existe.

Sans modèle, la page reste visible mais signale « non connecté », et une requête API valide peut retourner `503`. C'est **le comportement attendu**, pas un bug : GitHub Actions ne possède pas vos artefacts `.joblib`.

### 6.8. Étape G — Envoyer seulement son code sur GitHub

Exemple pour le membre `age` :

```bash
# Voir exactement ce qui a changé
git status

git diff -- ml_modules/age/adapter.py portal/catalog.py

# Ajouter SEULEMENT le code, la documentation et les tests modifiés
git add ml_modules/age/adapter.py portal/catalog.py portal/tests.py

git status --short

git commit -m "feat(age): integration modele regression"
git push -u origin feature/age
```

Adapte les chemins à ton module : `income`, `occupation`, `hours`, `education` ou `workclass`. **Ne pas utiliser `git add -f` pour un modèle.** Un `git add .` respecte normalement le `.gitignore`, mais `git add` ciblé est préférable pour examiner précisément les changements.

Sur GitHub : ouvrir une **Pull Request** de `feature/age` vers `main` (ou la branche d'intégration convenue), expliquer les entrées, les versions, les tests et les fichiers modifiés. Un autre membre révise, la CI exécute les tests Django, puis l'équipe fusionne. Si plusieurs personnes modifient `portal/catalog.py`, chacun ne doit toucher qu'à son propre `ModuleSpec` ; résoudre les conflits ensemble, sans écraser le travail des autres.

### 6.9. Comment récupérer ensuite les changements des collègues ?

Sur sa branche, d'abord enregistrer/committer son travail, puis :

```bash
git fetch origin
# Après fusion de la PR dans main :
git switch main
git pull --ff-only origin main
```

Pour démarrer une nouvelle fonctionnalité depuis la version à jour : `git switch -c feature/nouvelle-tache`.

Un collègue qui clone le dépôt reçoit **tout le code** des six modules, mais **aucun des six pipelines**. S'il veut exécuter les prédictions réelles de plusieurs membres sur sa machine, il lui faut copier **chacun** des `.joblib` approuvés dans son répertoire `ml_models/<slug>/` et installer des versions compatibles. Cela n'empêche pas de développer l'interface, d'exécuter les tests génériques ou de consulter les autres pages.

### 6.10. Contrôles de sécurité Git : aucun modèle ou dataset dans le dépôt

Le `.gitignore` du projet contient notamment :

```gitignore
*.joblib
*.pkl
*.pickle
*.csv
*.zip
.env
.venv/
```

Vérifie qu'un modèle est bien ignoré :

```bash
git check-ignore -v ml_models/education/pipeline.joblib
```

Vérifie les fichiers **déjà suivis** par Git, car `.gitignore` n'efface pas un fichier publié auparavant :

```bash
git ls-files '*.joblib' '*.pkl' '*.csv' '*.env'
```

Si un modèle a été ajouté par erreur à l'index Git, le retirer **sans le supprimer du disque** :

```bash
git rm --cached ml_models/education/pipeline.joblib
git commit -m "chore: stop tracking model artifact"
```

Si un secret ou un dataset sensible a déjà été rendu public, le retirer d'un commit récent ne suffit pas : informer l'équipe, révoquer les secrets concernés et traiter l'historique du dépôt avec une procédure adaptée.

### 6.11. Checklist avant une Pull Request

- [ ] J'ai travaillé sur `feature/<mon_module>` et non directement sur `main`.
- [ ] Je n'ai modifié que mon adaptateur, mon `ModuleSpec`, mes tests et mes dépendances nécessaires.
- [ ] Mon formulaire demande exactement les variables attendues par le pipeline, sans inclure la cible.
- [ ] Mon `predict(profile)` renvoie au minimum `{'label': '...'}` et des types JSON compatibles.
- [ ] Mon modèle et ses versions sont testés **localement**.
- [ ] `python manage.py check` et `python manage.py test` réussissent.
- [ ] `git status` ne montre aucun artefact ML, dataset, fichier `.env` ou base de données sensible.
- [ ] J'ai expliqué dans la PR comment un collègue peut installer mon artefact **hors Git**.

## 7. Publication initiale du squelette sur GitHub (responsable du repo)

Depuis le dossier `livrable_orentation` **uniquement si le dépôt Git n'a pas encore été initialisé** :

```bash
git init
git add .
git status --short
git commit -m "feat: initialise application Django collaborative"
git branch -M main
git remote add origin https://github.com/ORGANISATION_OU_COMPTE/livrable_orentation.git
git push -u origin main
```

**Avant le premier commit**, vérifier avec `git status` et `git ls-files` que le fichier du modèle n'est pas inclus. Si le dépôt GitHub existe déjà, le cloner d'abord puis copier les fichiers du squelette dedans et faire un commit/une Pull Request normale. **Ne pas forcer le push (`--force`) et ne pas réinitialiser un historique existant.**

Après le premier push, inviter les cinq collègues avec les permissions GitHub appropriées et leur envoyer ce README : ils commencent directement par **l'étape 6.2**.

## 8. Problèmes fréquents

| Problème | Solution |
|---|---|
| `python3.13: command not found` | Installer Python 3.13 puis créer le venv. |
| `No module named django` | Activer `.venv` et exécuter `pip install -r requirements.txt`. |
| `No module named xgboost` | Activer le même venv et installer les dépendances. |
| `libomp` manquant sur macOS | Installer OpenMP avec `brew install libomp`, puis relancer. |
| `FileNotFoundError: pipeline.joblib` | Vérifier le chemin `ml_models/education/pipeline.joblib`. |
| `Module non disponible` | Lancer `python scripts/doctor_model.py` et vérifier les 7 champs et les versions. |
| Erreur 403 sur l'API | Inclure cookie et token CSRF ; ne pas désactiver le CSRF. |
| Port 8000 déjà occupé | Lancer `python manage.py runserver 8001`. |
| Écran vide sans style | Vérifier que `STATICFILES_DIRS` pointe vers `static/`; recharger la page. |
| `ValueError` lors du chargement joblib | Utiliser Python et dépendances compatibles, ne jamais charger des artefacts non approuvés. |

## 9. Déploiement : après les tests locaux

Ne pas utiliser le serveur `runserver` en production. Avant une mise en ligne : secret Django via variable d'environnement, `DJANGO_DEBUG=0`, `ALLOWED_HOSTS`, serveur WSGI/ASGI, TLS/HTTPS, collecte des statiques, base adaptée, contrôle de débit, journaux sans données sensibles, et `python manage.py check --deploy`.

**Limites de l'évaluation :** ce modèle prédit un niveau à partir d'indicateurs socio-professionnels historiques américains. Il ne connaît pas directement le parcours scolaire confirmé d'un étudiant, et ses estimations ne constituent pas une admission ou une orientation définitive.

## 10. État des vérifications fournies

- ✅ Pipeline Education présent et testé dans la version de démonstration ; absent volontairement du ZIP source GitHub.
- ✅ Exemple de profil validé par le vrai pipeline (`0.5797`, seuil `0.52`).
- ✅ Syntaxe Python et arborescence contrôlées avant livraison.
- ⚠️ Le serveur et les tests Django complets doivent être exécutés dans un environnement où Django est installé. Environnement de génération sans accès réseau à Django.
