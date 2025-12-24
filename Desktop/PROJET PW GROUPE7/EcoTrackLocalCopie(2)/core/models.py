from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Enqueteur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    matricule = models.CharField(max_length=20, unique=True)
    telephone = models.CharField(max_length=15)
    date_inscription = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.matricule})"

class Etudiant(models.Model):
    SEXE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
    
    NIVEAU_CHOICES = [
        ('L1', 'Licence 1'),
        ('L2', 'Licence 2'),
        ('L3', 'Licence 3'),
        ('M1', 'Master 1'),
        ('M2', 'Master 2'),
        ('D', 'Doctorat'),
        ('AUTRE', 'Autre'),
    ]
    
    # Identification
    code_enquete = models.CharField(max_length=20, unique=True, verbose_name="Code d'enquête")
    enqueteur = models.ForeignKey(Enqueteur, on_delete=models.CASCADE, verbose_name="Enquêteur responsable")
    
    # Informations personnelles
    nom = models.CharField(max_length=100)
    age = models.IntegerField()
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    niveau = models.CharField(max_length=10, choices=NIVEAU_CHOICES)
    universite = models.CharField(max_length=100, verbose_name="Établissement")
    quartier = models.CharField(max_length=100)
    
    # Géolocalisation
    gps_lat = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    gps_lng = models.FloatField(null=True, blank=True, verbose_name="Longitude")
    
    # Métadonnées
    date_collecte = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, default='BROUILLON', choices=[
        ('BROUILLON', 'Brouillon'),
        ('COMPLET', 'Complet'),
        ('VERIFIE', 'Vérifié'),
        ('ANOMALIE', 'Anomalie détectée'),
    ])
    
    # Notes enquêteur
    notes = models.TextField(blank=True, verbose_name="Observations de l'enquêteur")
    photo = models.ImageField(upload_to='etudiants/', blank=True, null=True, verbose_name="Photo (optionnel)")
    
    def __str__(self):
        return f"{self.code_enquete} - {self.nom}"

class Depense(models.Model):
    CATEGORIE_CHOICES = [
        ('LOGEMENT', 'Logement (loyer, charges)'),
        ('NOURRITURE', 'Nourriture et boissons'),
        ('TRANSPORT', 'Transport'),
        ('SANTE', 'Santé et hygiène'),
        ('COMMUNICATION', 'Communication (internet, téléphone)'),
        ('FORMATION', 'Frais académiques'),
        ('DIVERTISSEMENT', 'Loisirs et divertissement'),
        ('HABILLEMENT', 'Habillement'),
        ('AUTRE', 'Autres dépenses'),
    ]
    
    # Liens
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='depenses')
    enqueteur = models.ForeignKey(Enqueteur, on_delete=models.CASCADE)
    
    # Données de base
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    montant = models.FloatField(verbose_name="Montant (FCFA)")
    
    # Contexte
    quartier = models.CharField(max_length=100, verbose_name="Quartier de la dépense")
    lieu_precis = models.CharField(max_length=200, blank=True, verbose_name="Lieu précis (marché, boutique...)")
    date_depense = models.DateField(verbose_name="Date de la dépense", default=timezone.now)
    
    # Validation et preuves
    photo = models.ImageField(upload_to='depenses/', blank=True, null=True, verbose_name="Photo du reçu/ticket")
    commentaire = models.TextField(blank=True, verbose_name="Commentaires")
    
    # Contrôle qualité
    est_valide = models.BooleanField(default=True, verbose_name="Donnée valide")
    anomalie = models.TextField(blank=True, verbose_name="Description de l'anomalie")
    date_saisie = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.etudiant.nom} - {self.categorie}: {self.montant} FCFA"

class Anomalie(models.Model):
    TYPE_CHOICES = [
        ('DOUBLON', 'Donnée en double'),
        ('HORS_NORME', 'Valeur hors norme'),
        ('INCOHERENCE', 'Incohérence logique'),
        ('MANQUANTE', 'Donnée manquante'),
        ('ERREUR_SAISIE', 'Erreur de saisie'),
    ]
    
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, null=True, blank=True)
    depense = models.ForeignKey(Depense, on_delete=models.CASCADE, null=True, blank=True, related_name='anomalies_depense')
    type_anomalie = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    gravite = models.CharField(max_length=10, choices=[
        ('FAIBLE', 'Faible'),
        ('MOYENNE', 'Moyenne'),
        ('ELEVEE', 'Élevée'),
    ])
    statut = models.CharField(max_length=20, default='A_TRAITER', choices=[
        ('A_TRAITER', 'À traiter'),
        ('EN_COURS', 'En cours de traitement'),
        ('RESOLUE', 'Résolue'),
        ('IGNOREE', 'Ignorée'),
    ])
    enqueteur = models.ForeignKey(Enqueteur, on_delete=models.CASCADE)
    date_detection = models.DateTimeField(auto_now_add=True)
    date_resolution = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Anomalie {self.type_anomalie} - {self.etudiant.nom if self.etudiant else 'Dépense'}"