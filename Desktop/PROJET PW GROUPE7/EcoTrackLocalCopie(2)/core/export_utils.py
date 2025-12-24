# core/export_utils.py
import csv
import json
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
import io
import base64
from django.utils import timezone
from .models import Etudiant, Depense, Anomalie

def export_etudiants_csv(etudiants):
    """Exporte la liste des étudiants en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="etudiants_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d_%H%M%S')
    )
    
    writer = csv.writer(response, delimiter=';')
    
    # En-tête
    writer.writerow([
        'Code Enquête', 'Nom', 'Âge', 'Sexe', 'Niveau', 
        'Université', 'Quartier', 'GPS Latitude', 'GPS Longitude',
        'Date Collecte', 'Statut', 'Nombre Dépenses', 'Total Dépenses (FCFA)'
    ])
    
    # Données
    for etudiant in etudiants:
        total_depenses = etudiant.depenses.aggregate(total=Sum('montant'))['total'] or 0
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
            etudiant.depenses.count(),
            f"{total_depenses:,.0f}".replace(',', ' ')
        ])
    
    return response

def export_depenses_csv(depenses):
    """Exporte la liste des dépenses en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="depenses_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d_%H%M%S')
    )
    
    writer = csv.writer(response, delimiter=';')
    
    # En-tête
    writer.writerow([
        'Étudiant', 'Code Enquête', 'Catégorie', 'Montant (FCFA)', 
        'Quartier', 'Lieu', 'Date Dépense', 'Date Saisie',
        'Photo', 'Commentaire', 'Valide', 'Anomalie'
    ])
    
    # Données
    for depense in depenses:
        writer.writerow([
            depense.etudiant.nom,
            depense.etudiant.code_enquete,
            depense.get_categorie_display(),
            f"{depense.montant:,.0f}".replace(',', ' '),
            depense.quartier,
            depense.lieu_precis or '',
            depense.date_depense.strftime('%d/%m/%Y'),
            depense.date_saisie.strftime('%d/%m/%Y %H:%M'),
            'Oui' if depense.photo else 'Non',
            depense.commentaire or '',
            'Oui' if depense.est_valide else 'Non',
            depense.anomalie_description or 'Aucune'
        ])
    
    return response

def export_anomalies_csv(anomalies):
    """Exporte la liste des anomalies en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="anomalies_{}.csv"'.format(
        timezone.now().strftime('%Y%m%d_%H%M%S')
    )
    
    writer = csv.writer(response, delimiter=';')
    
    # En-tête
    writer.writerow([
        'Type', 'Gravité', 'Statut', 'Description',
        'Étudiant', 'Code Enquête', 'Dépense Concernée',
        'Date Détection', 'Date Résolution', 'Enquêteur'
    ])
    
    # Données
    for anomalie in anomalies:
        writer.writerow([
            anomalie.get_type_anomalie_display(),
            anomalie.get_gravite_display(),
            anomalie.get_statut_display(),
            anomalie.description,
            anomalie.etudiant.nom if anomalie.etudiant else '',
            anomalie.etudiant.code_enquete if anomalie.etudiant else '',
            f"{anomalie.depense.categorie}: {anomalie.depense.montant} FCFA" if anomalie.depense else '',
            anomalie.date_detection.strftime('%d/%m/%Y %H:%M'),
            anomalie.date_resolution.strftime('%d/%m/%Y %H:%M') if anomalie.date_resolution else '',
            anomalie.enqueteur.user.username
        ])
    
    return response

def generate_pdf_report(etudiants, depenses, anomalies, enqueteur):
    """Génère un rapport PDF complet"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1e40af')
    )
    
    # Titre du rapport
    elements.append(Paragraph('Rapport EcoTrack Local', title_style))
    elements.append(Paragraph(f'Généré le: {timezone.now().strftime("%d/%m/%Y %H:%M")}', styles['Normal']))
    elements.append(Paragraph(f'Enquêteur: {enqueteur.user.username}', styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Section 1: Statistiques
    elements.append(Paragraph('Statistiques Générales', styles['Heading2']))
    
    stats_data = [
        ['Métrique', 'Valeur'],
        ['Nombre d\'étudiants', str(etudiants.count())],
        ['Nombre de dépenses', str(depenses.count())],
        ['Nombre d\'anomalies', str(anomalies.count())],
        ['Montant total collecté', f"{depenses.aggregate(total=Sum('montant'))['total'] or 0:,.0f} FCFA"],
        ['Quartiers couverts', str(etudiants.values('quartier').distinct().count())],
    ]
    
    stats_table = Table(stats_data, colWidths=[200, 200])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 30))
    
    # Section 2: Liste des étudiants
    if etudiants.exists():
        elements.append(Paragraph('Liste des Étudiants', styles['Heading2']))
        
        etud_data = [['Code', 'Nom', 'Âge', 'Quartier', 'Statut', 'Dépenses']]
        for etud in etudiants[:20]:  # Limiter à 20 pour le PDF
            etud_data.append([
                etud.code_enquete,
                etud.nom,
                str(etud.age),
                etud.quartier,
                etud.get_statut_display(),
                str(etud.depenses.count())
            ])
        
        etud_table = Table(etud_data, colWidths=[80, 120, 40, 100, 80, 60])
        etud_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(etud_table)
        if etudiants.count() > 20:
            elements.append(Paragraph(f"... et {etudiants.count() - 20} autres étudiants", styles['Italic']))
        elements.append(Spacer(1, 30))
    
    # Section 3: Anomalies critiques
    anomalies_critiques = anomalies.filter(gravite='ELEVEE', statut='A_TRAITER')
    if anomalies_critiques.exists():
        elements.append(Paragraph('Anomalies Critiques à Traiter', styles['Heading2']))
        elements.append(Paragraph('Ces anomalies nécessitent une attention immédiate:', styles['Normal']))
        
        for anomalie in anomalies_critiques[:10]:
            elements.append(Paragraph(f"• {anomalie.description}", styles['Normal']))
            elements.append(Paragraph(f"  Étudiant: {anomalie.etudiant.nom if anomalie.etudiant else 'Non spécifié'} | Type: {anomalie.get_type_anomalie_display()}", 
                                      styles['Italic']))
        
        elements.append(Spacer(1, 20))
    
    # Section 4: Recommandations
    elements.append(Paragraph('Recommandations', styles['Heading2']))
    recommandations = [
        "1. Compléter les enquêtes des étudiants marqués 'BROUILLON'",
        "2. Résoudre les anomalies critiques détectées",
        "3. Vérifier la cohérence des données de logement",
        "4. Standardiser la saisie des noms de quartiers",
        "5. Exporter régulièrement les données pour sauvegarde"
    ]
    
    for reco in recommandations:
        elements.append(Paragraph(reco, styles['Normal']))
    
    # Pied de page
    elements.append(Spacer(1, 50))
    elements.append(Paragraph('---', styles['Normal']))
    elements.append(Paragraph('EcoTrack Local - ISSEA AS3 2025', styles['Italic']))
    elements.append(Paragraph('Système de suivi des coûts de vie étudiants', styles['Italic']))
    
    # Générer le PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def export_full_pdf(request):
    """Vue pour exporter un PDF complet"""
    enqueteur = Enqueteur.objects.get(user=request.user)
    etudiants = Etudiant.objects.filter(enqueteur=enqueteur)
    depenses = Depense.objects.filter(enqueteur=enqueteur)
    anomalies = Anomalie.objects.filter(enqueteur=enqueteur)
    
    pdf_buffer = generate_pdf_report(etudiants, depenses, anomalies, enqueteur)
    
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_ecotrack_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    return response