from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Sum, Avg, Q, Max, Min
import csv
import io
import json
from datetime import datetime, date, timedelta
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from .models import Enqueteur, Etudiant, Depense, Anomalie
from .forms import EtudiantForm, DepenseForm, LoginForm
from .detecteur_anomalies import DetecteurAnomalies

# =========== UTILITAIRES ===========
def get_or_create_enqueteur(user):
    """Récupère ou crée un Enqueteur pour l'utilisateur"""
    try:
        return Enqueteur.objects.get(user=user)
    except Enqueteur.DoesNotExist:
        return Enqueteur.objects.create(
            user=user,
            matricule=f"USER{user.id:03d}",
            telephone="Non renseigné",
            date_inscription=timezone.now()
        )

# =========== AUTHENTIFICATION ===========
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenue {username}!')
                return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# =========== DASHBOARD ===========
@login_required
def dashboard(request):
    # Récupérer l'enquêteur
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Statistiques de base
    total_etudiants = Etudiant.objects.filter(enqueteur=enqueteur).count()
    total_depenses = Depense.objects.filter(enqueteur=enqueteur).count()
    montant_total = Depense.objects.filter(enqueteur=enqueteur).aggregate(Sum('montant'))['montant__sum'] or 0
    
    # Statistiques par sexe
    hommes_count = Etudiant.objects.filter(enqueteur=enqueteur, sexe='M').count()
    femmes_count = Etudiant.objects.filter(enqueteur=enqueteur, sexe='F').count()
    
    # Nombre de quartiers distincts
    quartiers_count = Etudiant.objects.filter(enqueteur=enqueteur)\
                                     .values('quartier')\
                                     .distinct()\
                                     .count()

    # Anomalies
    anomalies = Anomalie.objects.filter(enqueteur=enqueteur, statut='A_TRAITER').count()
    
    # Dernières anomalies
    dernieres_anomalies = Anomalie.objects.filter(enqueteur=enqueteur).order_by('-date_detection')[:5]
    
    # Calculer la moyenne générale
    moyenne_generale = montant_total / total_depenses if total_depenses > 0 else 0
    
    # ===== DONNÉES POUR CHART.JS =====
    # 1. Données pour le graphique des quartiers
    quartiers_stats = Etudiant.objects.filter(enqueteur=enqueteur)\
        .exclude(quartier='')\
        .values('quartier')\
        .annotate(count=Count('id'))\
        .order_by('-count')[:10]
    
    quartier_labels = [q['quartier'] if q['quartier'] else 'Non spécifié' for q in quartiers_stats]
    quartier_values = [q['count'] for q in quartiers_stats]
    
    # 2. Données pour le graphique des catégories
    categories_stats = Depense.objects.filter(enqueteur=enqueteur)\
        .values('categorie')\
        .annotate(total=Sum('montant'))\
        .order_by('-total')
    
    categorie_labels = []
    categorie_values = []
    # Couleurs pour chaque catégorie (pour Chart.js)
    couleur_map = {
        'LOGEMENT': '#3b82f6',
        'NOURRITURE': '#10b981', 
        'TRANSPORT': '#f59e0b',
        'SANTE': '#ef4444',
        'EDUCATION': '#8b5cf6',
        'COMMUNICATION': '#6366f1',
        'HABILLEMENT': '#14b8a6',
        'LOISIRS': '#ec4899',
        'AUTRES': '#94a3b8'
    }
    
    # Noms français pour l'affichage
    noms_francais = {
        'LOGEMENT': 'Logement',
        'NOURRITURE': 'Nourriture',
        'TRANSPORT': 'Transport',
        'SANTE': 'Santé',
        'EDUCATION': 'Éducation',
        'COMMUNICATION': 'Communication',
        'HABILLEMENT': 'Habillement',
        'LOISIRS': 'Loisirs',
        'AUTRES': 'Autres'
    }
    
    for cat in categories_stats:
        nom_fr = noms_francais.get(cat['categorie'], cat['categorie'])
        categorie_labels.append(nom_fr)
        categorie_values.append(float(cat['total']))
    
    # Liste des quartiers pour la comparaison
    quartiers_list = Etudiant.objects.filter(
        enqueteur=enqueteur
    ).exclude(quartier='').values_list('quartier', flat=True).distinct()
    
    # Préparer le contexte
    context = {
        'total_etudiants': total_etudiants,
        'total_depenses': total_depenses,
        'montant_total': montant_total,
        'moyenne_generale': round(moyenne_generale, 2),
        'anomalies': anomalies,
        'dernieres_anomalies': dernieres_anomalies,
        
        # Données pour Chart.js (format JSON)
        'quartier_labels_json': json.dumps(quartier_labels),
        'quartier_values_json': json.dumps(quartier_values),
        'categorie_labels_json': json.dumps(categorie_labels),
        'categorie_values_json': json.dumps(categorie_values),
        'categorie_couleurs_json': json.dumps([couleur_map.get(cat['categorie'], '#94a3b8') 
                                              for cat in categories_stats]),
        
        # Autres données
        'hommes_count': hommes_count,
        'femmes_count': femmes_count,
        'quartiers_count': quartiers_count,
        'quartiers_list': quartiers_list,
    }
    
    return render(request, 'core/dashboard.html', context)

# =========== PROFIL ===========
@login_required
def profil(request):
    enqueteur = get_or_create_enqueteur(request.user)
    
    if request.method == 'POST':
        # Gérer la mise à jour du profil
        matricule = request.POST.get('matricule')
        telephone = request.POST.get('telephone')
        
        if matricule:
            enqueteur.matricule = matricule
        if telephone:
            enqueteur.telephone = telephone
        
        # Gérer la photo
        if 'photo' in request.FILES:
            enqueteur.photo = request.FILES['photo']
        
        enqueteur.save()
        messages.success(request, 'Profil mis à jour avec succès')
        return redirect('profil')
    
    # ===== CALCULER LES STATISTIQUES COMPLÈTES =====
    total_etudiants = Etudiant.objects.filter(enqueteur=enqueteur).count()
    total_depenses = Depense.objects.filter(enqueteur=enqueteur).count()
    
    # Calcul du montant total et moyenne générale
    montant_total = Depense.objects.filter(enqueteur=enqueteur).aggregate(Sum('montant'))['montant__sum'] or 0
    
    if total_depenses > 0:
        moyenne_generale = montant_total / total_depenses
    else:
        moyenne_generale = 0
    
    quartiers = Etudiant.objects.filter(enqueteur=enqueteur)\
                               .values('quartier')\
                               .distinct()\
                               .count()
    
    anomalies_resolues = Anomalie.objects.filter(enqueteur=enqueteur, statut='RESOLUE').count()
    
    # Statistiques par sexe
    hommes_count = Etudiant.objects.filter(enqueteur=enqueteur, sexe='M').count()
    femmes_count = Etudiant.objects.filter(enqueteur=enqueteur, sexe='F').count()
    
    # Dernières activités
    dernieres_depenses = Depense.objects.filter(enqueteur=enqueteur).order_by('-date_saisie')[:5]
    dernieres_etudiants = Etudiant.objects.filter(enqueteur=enqueteur).order_by('-date_collecte')[:5]
    
    # Évolution ce mois (simplifié)
    date_debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    etudiants_ce_mois = Etudiant.objects.filter(
        enqueteur=enqueteur,
        date_collecte__gte=date_debut_mois
    ).count()
    
    # Calculer le pourcentage d'évolution
    if total_etudiants > 0 and etudiants_ce_mois > 0:
        pourcentage_evolution = (etudiants_ce_mois / total_etudiants) * 100
    else:
        pourcentage_evolution = 0
    
    context = {
        'enqueteur': enqueteur,
        'total_etudiants': total_etudiants,
        'total_depenses': total_depenses,
        'montant_total': montant_total,
        'moyenne_generale': moyenne_generale,
        'quartiers': quartiers,
        'anomalies_resolues': anomalies_resolues,
        'hommes_count': hommes_count,
        'femmes_count': femmes_count,
        'dernieres_depenses': dernieres_depenses,
        'dernieres_etudiants': dernieres_etudiants,
        'pourcentage_evolution': pourcentage_evolution,
        'etudiants_ce_mois': etudiants_ce_mois,
    }
    
    return render(request, 'core/profil.html', context)

@login_required
def parametres(request):
    """Page des paramètres"""
    return render(request, 'core/parametres.html')

# =========== GESTION ÉTUDIANTS ===========
@login_required
def etudiant_list(request):
    """Liste des étudiants avec filtres"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Récupérer les paramètres de recherche
    nom = request.GET.get('nom', '')
    quartier = request.GET.get('quartier', '')
    statut = request.GET.get('statut', '')
    periode = request.GET.get('periode', '')
    
    # Filtrer les étudiants
    etudiants = Etudiant.objects.filter(enqueteur=enqueteur)
    
    if nom:
        etudiants = etudiants.filter(nom__icontains=nom)
    
    if quartier:
        etudiants = etudiants.filter(quartier=quartier)
    
    if statut:
        etudiants = etudiants.filter(statut=statut)
    
    if periode:
        aujourdhui = timezone.now().date()
        if periode == 'today':
            etudiants = etudiants.filter(date_collecte__date=aujourdhui)
        elif periode == 'week':
            etudiants = etudiants.filter(date_collecte__date__gte=aujourdhui - timedelta(days=7))
        elif periode == 'month':
            etudiants = etudiants.filter(date_collecte__date__gte=aujourdhui - timedelta(days=30))
        elif periode == 'quarter':
            etudiants = etudiants.filter(date_collecte__date__gte=aujourdhui - timedelta(days=90))
    
    context = {
        'etudiants': etudiants,
        'filtres': {
            'nom': nom,
            'quartier': quartier,
            'statut': statut,
            'periode': periode,
        }
    }
    
    return render(request, 'core/etudiant_list.html', context)

@login_required
def etudiant_create(request):
    """Vue pour créer un nouvel étudiant"""
    # Récupérer l'enquêteur connecté
    enqueteur = get_or_create_enqueteur(request.user)
    
    if request.method == 'POST':
        form = EtudiantForm(request.POST, request.FILES)
        if form.is_valid():
            etudiant = form.save(commit=False)
            # ASSIGNER L'ENQUÊTEUR AVANT DE SAUVEGARDER
            etudiant.enqueteur = enqueteur
            etudiant.save()
            
            messages.success(request, f'Étudiant "{etudiant.nom}" créé avec succès !')
            return redirect('etudiant_detail', id=etudiant.id)  # Redirige vers les détails
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = EtudiantForm()
    
    return render(request, 'core/etudiant_form.html', {
        'form': form,
        'action': 'Créer',
        'enqueteur': enqueteur
    })

@login_required
def etudiant_detail(request, id):
    """Vue pour afficher les détails d'un étudiant"""
    enqueteur = get_or_create_enqueteur(request.user)
    etudiant = get_object_or_404(Etudiant, id=id, enqueteur=enqueteur)
    depenses = etudiant.depenses.all()
    total_depenses = depenses.aggregate(total=Sum('montant'))['total'] or 0
    
    context = {
        'etudiant': etudiant,
        'depenses': depenses,
        'total_depenses': total_depenses,
    }
    return render(request, 'core/etudiant_detail.html', context)

@login_required
def etudiant_update(request, id):
    """Vue pour modifier un étudiant"""
    enqueteur = get_or_create_enqueteur(request.user)
    etudiant = get_object_or_404(Etudiant, id=id, enqueteur=enqueteur)
    
    if request.method == 'POST':
        form = EtudiantForm(request.POST, request.FILES, instance=etudiant)
        if form.is_valid():
            form.save()
            messages.success(request, f'Étudiant "{etudiant.nom}" modifié avec succès !')
            return redirect('etudiant_detail', id=etudiant.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = EtudiantForm(instance=etudiant)
    
    return render(request, 'core/etudiant_form.html', {
        'form': form,
        'etudiant': etudiant,
        'action': 'Modifier'
    })

@login_required
def etudiant_delete(request, id):
    """Vue pour supprimer un étudiant (AJAX)"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        etudiant = get_object_or_404(Etudiant, id=id, enqueteur=enqueteur)
        etudiant.delete()
        return JsonResponse({'success': True, 'message': 'Étudiant supprimé avec succès'})
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@login_required
def etudiant_stats(request, id):
    """Vue pour afficher les statistiques d'un étudiant"""
    enqueteur = get_or_create_enqueteur(request.user)
    etudiant = get_object_or_404(Etudiant, id=id, enqueteur=enqueteur)
    depenses = etudiant.depenses.all()
    
    # Calcul des statistiques
    total_depenses = depenses.aggregate(total=Sum('montant'))['total'] or 0
    count_depenses = depenses.count()
    
    # Moyenne journalière
    dates_distinctes = depenses.values('date_depense').distinct().count()
    moyenne_journaliere = total_depenses / max(dates_distinctes, 1) if dates_distinctes > 0 else 0
    
    # Catégorie préférée
    categorie_preferee = None
    categorie_stats = depenses.values('categorie').annotate(
        total=Sum('montant')
    ).order_by('-total').first()
    if categorie_stats:
        categorie_preferee = categorie_stats['categorie']
    
    # Quartier fréquenté
    quartier_frequent = None
    quartier_stats = depenses.values('quartier').annotate(
        count=Count('id')
    ).order_by('-count').first()
    if quartier_stats:
        quartier_frequent = quartier_stats['quartier']
    
    # Statistiques par catégorie
    categories = depenses.values('categorie').annotate(
        total=Sum('montant'),
        count=Count('id')
    ).order_by('-total')
    
    stats = {
        'total_depenses': total_depenses,
        'count_depenses': count_depenses,
        'moyenne_journaliere': moyenne_journaliere,
        'categorie_preferee': categorie_preferee,
        'quartier_frequent': quartier_frequent,
    }
    
    context = {
        'etudiant': etudiant,
        'depenses': depenses,
        'stats': stats,
        'categories': categories,
    }
    
    return render(request, 'core/etudiant_stats.html', context)

# =========== GESTION DÉPENSES ===========
@login_required
def depense_create(request, etudiant_id):
    """Créer plusieurs dépenses en une fois pour un étudiant"""
    enqueteur = get_or_create_enqueteur(request.user)
    etudiant = get_object_or_404(Etudiant, id=etudiant_id, enqueteur=enqueteur)
    
    # Dépenses existantes de l'étudiant (pour affichage)
    depenses_existantes = Depense.objects.filter(etudiant=etudiant)
    
    if request.method == 'POST':
        # Récupérer toutes les catégories saisies
        categories = request.POST.getlist('categorie[]')
        montants = request.POST.getlist('montant[]')
        quartiers = request.POST.getlist('quartier[]')
        dates = request.POST.getlist('date_depense[]')
        commentaires = request.POST.getlist('commentaire[]')
        
        # Liste pour stocker les erreurs
        erreurs = []
        depenses_crees = 0
        
        # Parcourir toutes les dépenses saisies
        for i in range(len(categories)):
            categorie = categories[i]
            montant = montants[i]
            
            # Ignorer les lignes vides
            if categorie and montant:
                try:
                    # Créer la dépense
                    depense = Depense.objects.create(
                        etudiant=etudiant,
                        enqueteur=enqueteur,
                        categorie=categorie,
                        montant=float(montant),
                        quartier=quartiers[i] if i < len(quartiers) else etudiant.quartier,
                        date_depense=dates[i] if i < len(dates) and dates[i] else timezone.now().date(),
                        commentaire=commentaires[i] if i < len(commentaires) else ''
                    )
                    depenses_crees += 1
                    
                except Exception as e:
                    erreurs.append(f"Ligne {i+1}: {str(e)}")        

        if erreurs:
            for erreur in erreurs:
                messages.error(request, erreur)
        else:
            if depenses_crees > 0:
                messages.success(request, f'{depenses_crees} dépense(s) créée(s) avec succès !')
                
                # DÉTECTER LES ANOMALIES APRÈS LA CRÉATION
                detecteur = DetecteurAnomalies(enqueteur)
                detecteur.creer_anomalies_bd()
                
                # Rediriger vers les détails de l'étudiant
                return redirect('etudiant_detail', id=etudiant.id)
            else:
                messages.warning(request, 'Aucune dépense valide saisie.')
    
    # Préparer les catégories avec des montants par défaut (moyennes)
    categories_avec_montants = {
        'LOGEMENT': 15000,
        'NOURRITURE': 12000,
        'TRANSPORT': 8000,
        'SANTE': 5000,
        'EDUCATION': 10000,
        'COMMUNICATION': 5000,
        'HABILLEMENT': 6000,
        'LOISIRS': 4000,
        'AUTRES': 3000
    }
    
    context = {
        'etudiant': etudiant,
        'depenses_existantes': depenses_existantes,
        'categories_avec_montants': categories_avec_montants,
    }
    
    return render(request, 'core/depense_form.html', context)

@login_required
def depense_update(request, id):
    """Modifier une dépense"""
    enqueteur = get_or_create_enqueteur(request.user)
    depense = get_object_or_404(Depense, id=id, enqueteur=enqueteur)
    
    if request.method == 'POST':
        form = DepenseForm(request.POST, request.FILES, instance=depense)
        if form.is_valid():
            form.save()
            return redirect('etudiant_detail', id=depense.etudiant.id)
    else:
        form = DepenseForm(instance=depense)
    
    return render(request, 'core/depense_form.html', {
        'form': form,
        'action': 'Modifier'
    })

@login_required
def depense_delete(request, id):
    """Supprimer une dépense (AJAX)"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        depense = get_object_or_404(Depense, id=id, enqueteur=enqueteur)
        etudiant_id = depense.etudiant.id
        depense.delete()
        return JsonResponse({'success': True, 'etudiant_id': etudiant_id})
    return JsonResponse({'success': False}, status=405)

# =========== GESTION ANOMALIES ===========
@login_required
def anomalies_list(request):
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Détecter automatiquement les anomalies
    detecteur = DetecteurAnomalies(enqueteur)
    detecteur.creer_anomalies_bd()
    
    # Option: Générer des anomalies simulées (pour la démo)
    # DetecteurAnomalies.generer_anomalies_simulees(enqueteur, count=5)
    
    # Récupérer toutes les anomalies
    anomalies = Anomalie.objects.filter(enqueteur=enqueteur).order_by('-date_detection')
    
    # Statistiques
    stats = {
        'total': anomalies.count(),
        'critiques': anomalies.filter(gravite='ELEVEE', statut='A_TRAITER').count(),
        'moyennes': anomalies.filter(gravite='MOYENNE', statut='A_TRAITER').count(),
        'faibles': anomalies.filter(gravite='FAIBLE', statut='A_TRAITER').count(),
        'resolues': anomalies.filter(statut='RESOLUE').count(),
    }
    
    context = {
        'anomalies': anomalies,
        'stats': stats,
    }
    
    return render(request, 'core/anomalies.html', context)

@login_required
def resoudre_anomalie(request, anomalie_id):
    """Marquer une anomalie comme résolue"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        anomalie = get_object_or_404(Anomalie, id=anomalie_id, enqueteur=enqueteur)
        
        solution = request.POST.get('solution', '')
        notes = request.POST.get('notes', '')
        
        anomalie.statut = 'RESOLUE'
        anomalie.solution = solution
        anomalie.date_resolution = timezone.now()
        anomalie.save()
        
        messages.success(request, 'Anomalie marquée comme résolue')
        return redirect('anomalies_list')
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=400)

@login_required
def ignorer_anomalie(request, anomalie_id):
    """Ignorer une anomalie"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        anomalie = get_object_or_404(Anomalie, id=anomalie_id, enqueteur=enqueteur)
        anomalie.statut = 'IGNOREE'
        anomalie.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=400)

@login_required
def supprimer_anomalie(request, anomalie_id):
    """Supprimer une anomalie"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        anomalie = get_object_or_404(Anomalie, id=anomalie_id, enqueteur=enqueteur)
        anomalie.delete()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=400)

@login_required
def api_anomalies_stats(request):
    """API pour les statistiques d'anomalies"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    stats = {
        'total': Anomalie.objects.filter(enqueteur=enqueteur).count(),
        'critiques': Anomalie.objects.filter(enqueteur=enqueteur, gravite='ELEVEE', statut='A_TRAITER').count(),
        'moyennes': Anomalie.objects.filter(enqueteur=enqueteur, gravite='MOYENNE', statut='A_TRAITER').count(),
        'faibles': Anomalie.objects.filter(enqueteur=enqueteur, gravite='FAIBLE', statut='A_TRAITER').count(),
        'resolues': Anomalie.objects.filter(enqueteur=enqueteur, statut='RESOLUE').count(),
    }
    
    return JsonResponse(stats)

@login_required
def generer_anomalies_test(request):
    """Générer des anomalies de test (pour démonstration)"""
    enqueteur = get_or_create_enqueteur(request.user)
    DetecteurAnomalies.generer_anomalies_simulees(enqueteur, count=8)
    
    messages.success(request, 'Anomalies de test générées avec succès !')
    return redirect('anomalies_list')

# =========== COMPARAISON QUARTIERS ===========
@login_required
def comparaison_quartiers(request):
    """Page détaillée de comparaison par quartier"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Récupérer les statistiques par quartier
    quartiers = Etudiant.objects.filter(
        enqueteur=enqueteur
    ).values('quartier').annotate(
        nb_etudiants=Count('id'),
        nb_hommes=Count('id', filter=Q(sexe='M')),
        nb_femmes=Count('id', filter=Q(sexe='F')),
        age_moyen=Avg('age')
    )
    
    # Pour chaque quartier, calculer les dépenses
    quartiers_stats = []
    for q in quartiers:
        if q['quartier']:
            depenses = Depense.objects.filter(
                enqueteur=enqueteur,
                quartier=q['quartier']
            ).aggregate(
                total=Sum('montant'),
                moyenne=Avg('montant'),
                count=Count('id')
            )
            
            quartiers_stats.append({
                'quartier': q['quartier'],
                'nb_etudiants': q['nb_etudiants'],
                'nb_hommes': q['nb_hommes'] or 0,
                'nb_femmes': q['nb_femmes'] or 0,
                'age_moyen': q['age_moyen'] or 0,
                'total_depenses': depenses['total'] or 0,
                'moyenne_depenses': depenses['moyenne'] or 0,
                'nb_depenses': depenses['count'] or 0
            })
    
    # Trier par moyenne décroissante
    quartiers_stats.sort(key=lambda x: x['moyenne_depenses'], reverse=True)
    
    # Calculer les statistiques globales
    if quartiers_stats:
        plus_cher = quartiers_stats[0]
        moins_cher = quartiers_stats[-1]
        difference_max = plus_cher['moyenne_depenses'] - moins_cher['moyenne_depenses']
        moyenne_globale = sum(q['moyenne_depenses'] for q in quartiers_stats) / len(quartiers_stats)
    else:
        plus_cher = moins_cher = None
        difference_max = 0
        moyenne_globale = 0
    
    context = {
        'quartiers_stats': quartiers_stats,
        'plus_cher': plus_cher,
        'moins_cher': moins_cher,
        'difference_max': difference_max,
        'moyenne_globale': moyenne_globale,
    }
    
    return render(request, 'core/comparaison_quartiers.html', context)

@login_required
def api_comparaison_quartiers(request):
    """API pour comparer les quartiers"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Récupérer les paramètres
    quartiers = request.GET.getlist('quartiers[]')
    categorie = request.GET.get('categorie', 'TOUTES')
    
    if len(quartiers) < 2:
        return JsonResponse({'error': 'Sélectionnez au moins 2 quartiers'}, status=400)
    
    results = []
    
    for quartier in quartiers[:3]:  # Limiter à 3 quartiers max
        # Filtrer par catégorie
        depenses_query = Depense.objects.filter(
            enqueteur=enqueteur,
            quartier=quartier
        )
        
        if categorie != 'TOUTES':
            depenses_query = depenses_query.filter(categorie=categorie)
        
        # Calculer les statistiques
        stats = depenses_query.aggregate(
            moyenne=Avg('montant'),
            maximum=Max('montant'),
            minimum=Min('montant'),
            total=Sum('montant'),
            count=Count('id')
        )
        
        # Compter les étudiants
        nb_etudiants = Etudiant.objects.filter(
            enqueteur=enqueteur,
            quartier=quartier
        ).count()
        
        results.append({
            'quartier': quartier,
            'moyenne': float(stats['moyenne'] or 0),
            'maximum': float(stats['maximum'] or 0),
            'minimum': float(stats['minimum'] or 0),
            'total': float(stats['total'] or 0),
            'nb_depenses': stats['count'] or 0,
            'nb_etudiants': nb_etudiants
        })
    
    # Trier par moyenne décroissante
    results.sort(key=lambda x: x['moyenne'], reverse=True)
    
    # Calculer les différences
    if len(results) >= 2:
        difference = results[0]['moyenne'] - results[1]['moyenne']
        pourcentage = (difference / results[1]['moyenne'] * 100) if results[1]['moyenne'] > 0 else 0
    else:
        difference = 0
        pourcentage = 0
    
    return JsonResponse({
        'results': results,
        'difference': difference,
        'pourcentage': pourcentage,
        'categorie': categorie
    })

# =========== API ENDPOINTS ===========
@login_required
def api_quartiers_stats(request):
    """API pour les statistiques par quartier"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    quartiers = Etudiant.objects.filter(
        enqueteur=enqueteur
    ).values('quartier').annotate(
        nb_etudiants=Count('id'),
        nb_depenses=Count('depenses'),
        total_depenses=Sum('depenses__montant'),
        moyenne_depenses=Avg('depenses__montant')
    )
    
    data = []
    for q in quartiers:
        if q['quartier']:
            data.append({
                'nom': q['quartier'],
                'etudiants': q['nb_etudiants'] or 0,
                'depenses': q['nb_depenses'] or 0,
                'moyenne': float(q['moyenne_depenses'] or 0),
                'total': float(q['total_depenses'] or 0)
            })
    
    return JsonResponse(data, safe=False)

@login_required
def api_dashboard_stats(request):
    """API pour les statistiques du dashboard"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    stats = {
        'total_etudiants': Etudiant.objects.filter(enqueteur=enqueteur).count(),
        'total_depenses': Depense.objects.filter(enqueteur=enqueteur).count(),
        'total_quartiers': Etudiant.objects.filter(enqueteur=enqueteur)
                                        .values('quartier')
                                        .distinct()
                                        .count(),
        'anomalies_resolues': Anomalie.objects.filter(
            enqueteur=enqueteur, 
            statut='RESOLUE'
        ).count(),
    }
    
    return JsonResponse(stats)

@login_required
def api_sexe_stats(request):
    """API pour les statistiques par sexe"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    stats = Etudiant.objects.filter(enqueteur=enqueteur).values('sexe').annotate(
        count=Count('id'),
        moyenne_depenses=Avg('depenses__montant')
    )
    
    data = {
        'hommes': 0,
        'femmes': 0,
        'ratio': '0:0'
    }
    
    for stat in stats:
        if stat['sexe'] == 'M':
            data['hommes'] = stat['count']
        elif stat['sexe'] == 'F':
            data['femmes'] = stat['count']
    
    if data['femmes'] > 0:
        data['ratio'] = f"{data['hommes']}:{data['femmes']}"
    elif data['hommes'] > 0:
        data['ratio'] = f"{data['hommes']}:0"
    
    return JsonResponse(data)

@login_required
def api_evolution_depenses(request):
    """API pour l'évolution des dépenses (7 derniers jours)"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    # 7 derniers jours
    dates = []
    montants = []
    
    for i in range(7):
        date = timezone.now() - timedelta(days=i)
        
        total = Depense.objects.filter(
            enqueteur=enqueteur,
            date_saisie__date=date.date()
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        
        dates.append(date.strftime('%a'))
        montants.append(float(total))
    
    # Inverser pour avoir du plus ancien au plus récent
    dates.reverse()
    montants.reverse()
    
    return JsonResponse({
        'dates': dates,
        'montants': montants
    })

# Dans views.py, tu dois avoir cette fonction :
@login_required
def api_rechercher_etudiants(request):
    """API pour rechercher des étudiants"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Récupérer les filtres
    nom = request.GET.get('nom', '')
    quartier = request.GET.get('quartier', '')
    sexe = request.GET.get('sexe', '')
    
    # Construire la requête
    queryset = Etudiant.objects.filter(enqueteur=enqueteur)
    
    if nom:
        queryset = queryset.filter(nom__icontains=nom)
    if quartier:
        queryset = queryset.filter(quartier=quartier)
    if sexe:
        queryset = queryset.filter(sexe=sexe)
    
    # Sérialiser les résultats
    etudiants = []
    for etud in queryset:
        etudiants.append({
            'id': etud.id,
            'nom': etud.nom,
            'age': etud.age,
            'sexe': etud.get_sexe_display(),
            'quartier': etud.quartier,
            'niveau': etud.get_niveau_display(),
            'statut': etud.statut,
            'code_enquete': etud.code_enquete,
            'nb_depenses': etud.depenses.count()
        })
    
    return JsonResponse({'etudiants': etudiants})

# =========== EXPORT ===========
@login_required
def export_etudiants_csv(request):
    """Exporte les étudiants en CSV"""
    enqueteur = get_or_create_enqueteur(request.user)
    etudiants = Etudiant.objects.filter(enqueteur=enqueteur)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="etudiants_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response, delimiter=';')
    
    # En-tête
    writer.writerow([
        'Code Enquête', 'Nom', 'Âge', 'Sexe', 'Niveau', 
        'Université', 'Quartier', 'GPS Latitude', 'GPS Longitude',
        'Date Collecte', 'Statut', 'Nombre Dépenses'
    ])
    
    # Données
    for etudiant in etudiants:
        writer.writerow([
            etudiant.code_enquete,
            etudiant.nom,
            etudiant.age,
            etudiant.get_sexe_display(),
            etudiant.get_niveau_display(),
            etudiant.universite,
            etudiant.quartier,
            etudiant.gps_lat or '',
            etudiant.gps_lng or '',
            etudiant.date_collecte.strftime('%d/%m/%Y %H:%M'),
            etudiant.get_statut_display(),
            etudiant.depenses.count()
        ])
    
    return response

@login_required
def export_rapport_pdf(request):
    """Exporte un rapport PDF (simplifié pour l'instant)"""
    enqueteur = get_or_create_enqueteur(request.user)
    
    # Pour l'instant, retourne un simple message
    # On implémentera ReportLab plus tard si besoin
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_{timezone.now().strftime("%Y%m%d")}.pdf"'
    response.write(b'Fonctionnalite PDF en cours de developpement.')
    
    return response

@login_required
def export_selection_csv(request):
    """Exporter la sélection en CSV"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        ids = request.POST.getlist('ids[]')
        etudiants = Etudiant.objects.filter(id__in=ids, enqueteur=enqueteur)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="selection_etudiants.csv"'
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Code', 'Nom', 'Âge', 'Sexe', 'Université', 'Quartier', 'Date'])
        
        for etudiant in etudiants:
            writer.writerow([
                etudiant.code_enquete,
                etudiant.nom,
                etudiant.age,
                etudiant.get_sexe_display(),
                etudiant.universite,
                etudiant.quartier,
                etudiant.date_collecte.strftime('%d/%m/%Y'),
            ])
        
        return response
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=400)

@login_required
def marquer_verifies(request):
    """Marquer plusieurs étudiants comme vérifiés"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        ids = request.POST.getlist('ids[]')
        statut = request.POST.get('statut', 'VERIFIE')
        
        Etudiant.objects.filter(id__in=ids, enqueteur=enqueteur).update(statut=statut)
        return JsonResponse({'success': True, 'count': len(ids)})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def supprimer_selection(request):
    """Supprimer plusieurs étudiants"""
    if request.method == 'POST':
        enqueteur = get_or_create_enqueteur(request.user)
        ids = request.POST.getlist('ids[]')
        Etudiant.objects.filter(id__in=ids, enqueteur=enqueteur).delete()
        return JsonResponse({'success': True, 'count': len(ids)})
    
    return JsonResponse({'success': False}, status=400)