# Dishwasher Duty – Guide utilisateur (Français)

Dishwasher Duty retient **qui vide le lave-vaisselle** et tient des statistiques.

## 1. Fonctionnement
Il surveille un capteur de votre lave-vaisselle (par ex. Home Connect « Operation state »).
Quand il passe de **En marche → Terminé**, un cycle revendicable s'ouvre. Celui qui vide appuie
sur son bouton (ou appelle un service) et reçoit un crédit de **1,0**. Si plusieurs personnes
participent, le 1,0 est partagé équitablement.

## 2. Installation
- **HACS :** ⋮ → *Dépôts personnalisés* → ajoutez ce dépôt comme **Intégration**, téléchargez,
  redémarrez HA.
- **Manuel :** copiez `custom_components/dishwasher_duty/` dans `<config>/custom_components/`,
  redémarrez.
- Puis *Paramètres → Appareils et services → Ajouter une intégration → « Dishwasher Duty »*.

## 3. Configuration
- **Capteur source :** le capteur d'état de votre machine.
- **Valeur « En marche »/« Terminé »** (deuxième étape) : choisissez-les dans la liste des états
  proposés par votre capteur ou saisissez votre propre valeur. Home Connect utilise `run` et
  `finished` (valeurs par défaut). La casse n'a pas d'importance. En cas de doute, consultez
  *Outils de développement → États*.
- **Personnes autorisées :** les entités `person` qui vident.
- **Vidage partagé** (activé par défaut) + **fenêtre de co-revendication** (90 s).

## 4. Au quotidien
- Après avoir vidé, appuyez sur votre **bouton** : `button.dishwasher_duty_claim_<nom>`.
- Partagé ? Chacun appuie sur son bouton dans la fenêtre — le 1,0 est partagé.
- Appui par erreur ? Utilisez `dishwasher_duty.cancel_claim` tant que la fenêtre est ouverte.

## 5. Entités
- `binary_sensor.dishwasher_duty_claimable` – « on » tant que revendicable.
- `sensor.dishwasher_duty_total_cycles` – nombre de cycles terminés.
- `sensor.dishwasher_duty_<nom>` – crédits par personne (attributs : jour/semaine/mois/année).

## 6. Obtenir des statistiques
```yaml
action: dishwasher_duty.get_statistics
data:
  start: "2026-01-01 00:00:00"
  end: "2026-12-31 23:59:59"
response_variable: stats
```
Renvoie le total des cycles, les cycles non revendiqués, par personne (participations + crédits)
et une liste chronologique.

## 7. Remarques
- `unavailable`/`unknown` sont ignorés : *run → unavailable → finished* compte comme un cycle ;
  *unavailable → finished* sans marche préalable, non.
- `dishwasher_duty.cancel_claim` renvoie une erreur si aucun cycle n'est ouvert.
- Appuyer plusieurs fois est sans effet (une contribution par personne/cycle).
- `dishwasher_duty.reset_statistics` efface l'historique (tout ou par personne) — à utiliser avec
  précaution.
