# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ===== PAGES PRINCIPALES =====
    path('', views.dashboard, name='dashboard'),
    path('profil/', views.profil, name='profil'),
    path('parametres/', views.parametres, name='parametres'),
    
    # ===== ÉTUDIANTS =====
    path('etudiants/', views.etudiant_list, name='etudiant_list'),
    path('etudiant/nouveau/', views.etudiant_create, name='etudiant_create'),
    path('etudiant/<int:id>/', views.etudiant_detail, name='etudiant_detail'),
    path('etudiant/<int:id>/modifier/', views.etudiant_update, name='etudiant_update'),
    path('etudiant/<int:id>/supprimer/', views.etudiant_delete, name='etudiant_delete'),
    path('etudiant/<int:id>/stats/', views.etudiant_stats, name='etudiant_stats'),
    
    # ===== DÉPENSES =====
    path('etudiant/<int:etudiant_id>/depenses/nouvelle/', views.depense_create, name='depense_create'),
    path('depense/<int:id>/modifier/', views.depense_update, name='depense_update'),
    path('depense/<int:id>/supprimer/', views.depense_delete, name='depense_delete'),
    
    # ===== ANOMALIES =====
    path('anomalies/', views.anomalies_list, name='anomalies_list'),
    path('anomalies/resoudre/<int:anomalie_id>/', views.resoudre_anomalie, name='resoudre_anomalie'),
    path('anomalies/ignorer/<int:anomalie_id>/', views.ignorer_anomalie, name='ignorer_anomalie'),
    path('anomalies/supprimer/<int:anomalie_id>/', views.supprimer_anomalie, name='supprimer_anomalie'),
    path('anomalies/generer-test/', views.generer_anomalies_test, name='generer_anomalies_test'),
    
    # ===== EXPORTS =====
    path('export/etudiants/csv/', views.export_etudiants_csv, name='export_etudiants_csv'),
    path('export/rapport/pdf/', views.export_rapport_pdf, name='export_rapport_pdf'),
    path('etudiants/export-selection/', views.export_selection_csv, name='export_selection'),
    path('etudiants/marquer-verifies/', views.marquer_verifies, name='marquer_verifies'),
    path('etudiants/supprimer-selection/', views.supprimer_selection, name='supprimer_selection'),
    
    # ===== API / AJAX =====
    path('api/quartiers-stats/', views.api_quartiers_stats, name='api_quartiers_stats'),
    path('api/dashboard-stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/sexe-stats/', views.api_sexe_stats, name='api_sexe_stats'),
    path('api/evolution-depenses/', views.api_evolution_depenses, name='api_evolution_depenses'),
    path('api/rechercher-etudiants/', views.api_rechercher_etudiants, name='api_rechercher_etudiants'),
    path('api/anomalies/stats/', views.api_anomalies_stats, name='api_anomalies_stats'),
    
    # ===== AUTHENTIFICATION =====
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ===== COMPARAISON QUARTIERS =====
    path('comparaison-quartiers/', views.comparaison_quartiers, name='comparaison_quartiers'),
    path('api/comparaison-quartiers/', views.api_comparaison_quartiers, name='api_comparaison_quartiers'),
    path('etudiant/<int:id>/detail/', views.etudiant_detail, name='etudiant_detail_old'),
]