# core/detecteur_anomalies.py
from django.utils import timezone
from .models import Etudiant, Depense, Anomalie, Enqueteur
from django.db.models import Avg

class DetecteurAnomalies:
    """Classe pour détecter automatiquement les anomalies dans les données"""
    
    def __init__(self, enqueteur):
        self.enqueteur = enqueteur
    
    def detecter_toutes_anomalies(self):
        """Détecte tous les types d'anomalies"""
        anomalies = []
        
        anomalies.extend(self.detecter_doublons_etudiants())
        anomalies.extend(self.detecter_depenses_hors_norme())
        anomalies.extend(self.detecter_incoherences_age())
        anomalies.extend(self.detecter_donnees_manquantes())
        
        return anomalies
    
    def detecter_doublons_etudiants(self):
        """Détecte les étudiants en doublon"""
        anomalies = []
        
        etudiants = Etudiant.objects.filter(enqueteur=self.enqueteur)
        
        for etudiant in etudiants:
            doublons = Etudiant.objects.filter(
                enqueteur=self.enqueteur,
                nom__iexact=etudiant.nom
            ).exclude(id=etudiant.id)
            
            if doublons.exists():
                anomalies.append({
                    'etudiant': etudiant,
                    'type': 'DOUBLON',
                    'gravite': 'MOYENNE',
                    'description': f"Étudiant potentiellement en doublon : {etudiant.nom}",
                    'solution': "Vérifier si c'est le même étudiant ou supprimer le doublon"
                })
        
        return anomalies
    
    def detecter_depenses_hors_norme(self):
        """Détecte les dépenses avec des montants anormaux"""
        anomalies = []
        
        limites = {
            'LOGEMENT': {'min': 5000, 'max': 50000},
            'NOURRITURE': {'min': 2000, 'max': 30000},
            'TRANSPORT': {'min': 1000, 'max': 20000},
            'SANTE': {'min': 1000, 'max': 100000},
            'EDUCATION': {'min': 1000, 'max': 50000},
            'COMMUNICATION': {'min': 500, 'max': 20000},
            'HABILLEMENT': {'min': 1000, 'max': 30000},
            'LOISIRS': {'min': 500, 'max': 20000},
            'AUTRES': {'min': 0, 'max': 50000},
        }
        
        depenses = Depense.objects.filter(enqueteur=self.enqueteur)
        
        for depense in depenses:
            limites_cat = limites.get(depense.categorie, {'min': 0, 'max': 100000})
            
            if depense.montant < limites_cat['min']:
                anomalies.append({
                    'depense': depense,
                    'type': 'HORS_NORME',
                    'gravite': 'FAIBLE',
                    'description': f"Dépense très faible en {depense.get_categorie_display()}: {depense.montant} FCFA",
                    'solution': f"Vérifier le montant. Minimum attendu: {limites_cat['min']} FCFA"
                })
            
            if depense.montant > limites_cat['max']:
                anomalies.append({
                    'depense': depense,
                    'type': 'HORS_NORME',
                    'gravite': 'ELEVEE',
                    'description': f"Dépense très élevée en {depense.get_categorie_display()}: {depense.montant} FCFA",
                    'solution': f"Vérifier le montant. Maximum attendu: {limites_cat['max']} FCFA"
                })
        
        return anomalies
    
    def detecter_incoherences_age(self):
        """Détecte les incohérences d'âge avec le niveau d'études"""
        anomalies = []
        
        etudiants = Etudiant.objects.filter(enqueteur=self.enqueteur)
        
        for etudiant in etudiants:
            if etudiant.age and etudiant.niveau:
                incoherent = False
                message = ""
                
                if etudiant.niveau == 'LICENCE1' and (etudiant.age < 18 or etudiant.age > 25):
                    incoherent = True
                    message = f"Âge ({etudiant.age} ans) atypique pour Licence 1"
                elif etudiant.niveau == 'LICENCE2' and (etudiant.age < 19 or etudiant.age > 26):
                    incoherent = True
                    message = f"Âge ({etudiant.age} ans) atypique pour Licence 2"
                elif etudiant.niveau == 'LICENCE3' and (etudiant.age < 20 or etudiant.age > 27):
                    incoherent = True
                    message = f"Âge ({etudiant.age} ans) atypique pour Licence 3"
                elif etudiant.niveau == 'MASTER1' and (etudiant.age < 21 or etudiant.age > 30):
                    incoherent = True
                    message = f"Âge ({etudiant.age} ans) atypique pour Master 1"
                elif etudiant.niveau == 'MASTER2' and (etudiant.age < 22 or etudiant.age > 31):
                    incoherent = True
                    message = f"Âge ({etudiant.age} ans) atypique pour Master 2"
                
                if incoherent:
                    anomalies.append({
                        'etudiant': etudiant,
                        'type': 'INCOHERENCE',
                        'gravite': 'MOYENNE',
                        'description': message,
                        'solution': "Vérifier l'âge ou le niveau de l'étudiant"
                    })
        
        return anomalies
    
    def detecter_donnees_manquantes(self):
        """Détecte les données obligatoires manquantes"""
        anomalies = []
        
        # Étudiants sans dépenses
        etudiants_sans_depenses = Etudiant.objects.filter(
            enqueteur=self.enqueteur,
            depenses__isnull=True
        )
        
        for etudiant in etudiants_sans_depenses:
            anomalies.append({
                'etudiant': etudiant,
                'type': 'MANQUANTE',
                'gravite': 'ELEVEE',
                'description': f"Étudiant sans aucune dépense enregistrée: {etudiant.nom}",
                'solution': "Ajouter au moins une dépense pour cet étudiant"
            })
        
        # Étudiants sans quartier
        etudiants_sans_quartier = Etudiant.objects.filter(
            enqueteur=self.enqueteur,
            quartier__isnull=True
        )
        
        for etudiant in etudiants_sans_quartier:
            anomalies.append({
                'etudiant': etudiant,
                'type': 'MANQUANTE',
                'gravite': 'FAIBLE',
                'description': f"Étudiant sans quartier renseigné: {etudiant.nom}",
                'solution': "Compléter le quartier de résidence"
            })
        
        return anomalies
    
    def creer_anomalies_bd(self):
        """Crée les anomalies détectées dans la base de données"""
        anomalies_detectees = self.detecter_toutes_anomalies()
        
        for anomalie_data in anomalies_detectees:
            existe = Anomalie.objects.filter(
                enqueteur=self.enqueteur,
                description=anomalie_data['description'],
                statut='A_TRAITER'
            ).exists()
            
            if not existe:
                Anomalie.objects.create(
                    etudiant=anomalie_data.get('etudiant'),
                    depense=anomalie_data.get('depense'),
                    enqueteur=self.enqueteur,
                    type_anomalie=anomalie_data['type'],
                    gravite=anomalie_data['gravite'],
                    statut='A_TRAITER',
                    description=anomalie_data['description'],
                    solution=anomalie_data.get('solution', ''),
                    date_detection=timezone.now()
                )
    
    @staticmethod
    def generer_anomalies_simulees(enqueteur, count=5):
        """Génère des anomalies simulées pour la démonstration"""
        etudiants = Etudiant.objects.filter(enqueteur=enqueteur)[:3]
        
        if not etudiants.exists():
            return []
        
        anomalies_simulees = [
            {
                'etudiant': etudiants[0],
                'type': 'DOUBLON',
                'gravite': 'MOYENNE',
                'description': f"Étudiant potentiellement en doublon : {etudiants[0].nom}",
                'solution': "Vérifier les informations et supprimer le doublon si nécessaire"
            },
            {
                'etudiant': etudiants[1] if len(etudiants) > 1 else etudiants[0],
                'type': 'HORS_NORME',
                'gravite': 'ELEVEE',
                'description': "Dépense de logement anormalement élevée : 75 000 FCFA",
                'solution': "Vérifier le montant de la dépense"
            },
            {
                'etudiant': etudiants[2] if len(etudiants) > 2 else etudiants[0],
                'type': 'INCOHERENCE',
                'gravite': 'MOYENNE',
                'description': f"Âge (35 ans) atypique pour un étudiant en Licence 1",
                'solution': "Vérifier l'âge ou le niveau de l'étudiant"
            },
            {
                'etudiant': etudiants[0],
                'type': 'MANQUANTE',
                'gravite': 'FAIBLE',
                'description': f"Données GPS manquantes pour {etudiants[0].nom}",
                'solution': "Ajouter les coordonnées GPS de résidence"
            },
            {
                'etudiant': etudiants[1] if len(etudiants) > 1 else etudiants[0],
                'type': 'FORMAT',
                'gravite': 'FAIBLE',
                'description': "Format de numéro de téléphone invalide",
                'solution': "Corriger le format du numéro de téléphone"
            }
        ]
        
        # Créer les anomalies simulées
        for i, anomalie_data in enumerate(anomalies_simulees[:count]):
            if not Anomalie.objects.filter(
                enqueteur=enqueteur,
                description=anomalie_data['description']
            ).exists():
                Anomalie.objects.create(
                    etudiant=anomalie_data['etudiant'],
                    enqueteur=enqueteur,
                    type_anomalie=anomalie_data['type'],
                    gravite=anomalie_data['gravite'],
                    statut='A_TRAITER',
                    description=anomalie_data['description'],
                    solution=anomalie_data['solution']
                )