"""Noms des groupes et recommandations du module occupation (modèle à 9 variables).

Les chiffres viennent du notebook (profils moyens des 3 groupes). Les recommandations sont des pistes
d'orientation fondées sur ces moyennes : elles décrivent des tendances observées dans des données de 1994,
pas des garanties. Le sexe n'est jamais utilisé pour recommander quoi que ce soit.
"""


def fr(x, nd=1):
    """Nombre au format français (virgule), sans zéro inutile."""
    s = f"{x:.{nd}f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


GROUPES = {
    "0": dict(nom="Les Expérimentés", slogan="Beaucoup d’années de métier, des études plus courtes",
              taille=23.3, age=53.5, heures=36.2, etudes=8.3, hauts=9, metier="Craft-repair"),
    "1": dict(nom="Les Nouveaux Départs", slogan="Jeunes, en début de parcours, souvent célibataires",
              taille=39.2, age=27.1, heures=36.0, etudes=9.8, hauts=2, metier="Adm-clerical"),
    "2": dict(nom="Les Bâtisseurs", slogan="Carrière installée, longues semaines, revenus élevés",
              taille=37.6, age=41.5, heures=47.7, etudes=11.4, hauts=56, metier="Prof-specialty"),
}
NOMS_GROUPES = {k: v["nom"] for k, v in GROUPES.items()}
CIBLE = "2"  # groupe où la part de revenus supérieurs à 50K est la plus élevée

PISTES = {
    "0": [
        ("Faire reconnaître votre expérience",
         "Une validation des acquis ou une certification courte peut mettre en valeur des années de pratique qu’un diplôme ne montre pas.",
         "Votre profil a le niveau d’études le plus bas (8,3 ans) mais la plus grande ancienneté (53 ans en moyenne)."),
        ("Viser une formation ciblée plutôt qu’un long cursus",
         "Un module de quelques mois sur une compétence précise (gestion d’équipe, technique, numérique) est plus réaliste qu’une reprise d’études complète.",
         "Chez Les Bâtisseurs, 56 % gagnent plus de 50K avec 11,4 ans d’études en moyenne, contre 9 % dans votre profil."),
        ("Transmettre votre savoir-faire",
         "Tutorat, formation interne ou accompagnement de jeunes : une façon de valoriser votre métier (Craft-repair est le plus fréquent dans votre profil).",
         "Idée d’orientation : elle ne vient pas directement des chiffres du groupe."),
    ],
    "1": [
        ("Investir tôt dans une formation",
         "Alternance, certification ou licence en parallèle d’un emploi : c’est l’écart de formation qui distingue le plus votre profil de celui des Bâtisseurs.",
         "Les Bâtisseurs ont 11,4 ans d’études en moyenne et 56 % gagnent plus de 50K ; seulement 2 % dans votre profil."),
        ("Viser des fonctions spécialisées",
         "Faire évoluer un poste administratif ou de service vers une fonction spécialisée ou technique élargit les perspectives.",
         "Dans votre profil, la fonction la plus fréquente est Adm-clerical (16 %) ; chez Les Bâtisseurs, c’est Prof-specialty (21 %)."),
        ("Utiliser votre disponibilité pour apprendre",
         "Avec environ 36 h par semaine, il reste de la marge pour combiner emploi et cours du soir ou formation à distance.",
         "Les Bâtisseurs travaillent en moyenne 47,7 h par semaine : sans forcément viser ce rythme, apprendre est un meilleur levier que travailler plus."),
    ],
    "2": [
        ("Protéger votre équilibre de vie",
         "Une semaine longue est la norme dans votre profil : planifier des pauses et de la récupération aide à tenir dans la durée.",
         "Votre profil travaille 47,7 h par semaine en moyenne, soit environ 12 h de plus que les deux autres profils."),
        ("Consolider une expertise",
         "Spécialisation, certification avancée ou mentorat : votre profil est déjà celui où l’on gagne le plus, l’enjeu est de s’y maintenir.",
         "56 % de votre profil gagne plus de 50K ; Prof-specialty est la fonction la plus fréquente (21 %)."),
        ("Penser à la sécurité financière",
         "Épargne, assurance, préparation de la suite de carrière : c’est le profil où l’on déclare le plus de gains ou pertes de capital.",
         "21 % de votre profil déclare du capital (contre 6 % chez Les Nouveaux Départs). Information générale, pas un conseil financier."),
    ],
}


def _compare(label, vous, moyenne, unite, nd=1):
    ecart = vous - moyenne
    if abs(ecart) < (1 if unite == "ans" else 2):
        sens = "proche de la moyenne de votre profil"
    else:
        sens = ("au-dessus" if ecart > 0 else "en dessous") + " de la moyenne de votre profil"
    return dict(label=label, vous=f"{fr(vous, 0)} {unite}", moyenne=f"{fr(moyenne, nd)} {unite}", sens=sens)


def recommander(segment, profil):
    """Recommandations d'orientation pour le groupe `segment`, personnalisées avec les valeurs saisies."""
    g = GROUPES.get(str(segment))
    if g is None:
        return None
    age, etudes, heures = profil.get("age"), profil.get("education_num"), profil.get("hours_per_week")
    comparaisons = []
    if age is not None:
        comparaisons.append(_compare("Âge", float(age), g["age"], "ans"))
    if etudes is not None:
        comparaisons.append(_compare("Années d’études", float(etudes), g["etudes"], "ans"))
    if heures is not None:
        comparaisons.append(_compare("Heures par semaine", float(heures), g["heures"], "h"))

    cible = GROUPES[CIBLE]
    if str(segment) == CIBLE:
        ecart = f"Vous êtes dans le profil où la part de revenus supérieurs à 50K est la plus élevée ({cible['hauts']} %)."
    elif etudes is not None and float(etudes) < cible["etudes"]:
        d = cible["etudes"] - float(etudes)
        ecart = (f"Par rapport au profil « {cible['nom']} » ({cible['hauts']} % y gagnent plus de 50K), il vous manque environ "
                 f"{fr(d)} an{'s' if d >= 2 else ''} d’études en moyenne.")
    else:
        ecart = (f"Votre niveau d’études atteint déjà celui du profil « {cible['nom']} » ({fr(cible['etudes'])} ans) : "
                 f"l’écart se joue plutôt sur l’expérience et le type de poste.")
    return dict(
        nom=g["nom"], slogan=g["slogan"], taille=fr(g["taille"]) + " %",
        comparaisons=comparaisons, ecart=ecart,
        pistes=[dict(titre=t, texte=x, preuve=p) for t, x, p in PISTES[str(segment)]],
        avertissement="Pistes indicatives tirées de moyennes observées dans des données de recensement de 1994 : elles décrivent des tendances, pas des garanties.",
    )
