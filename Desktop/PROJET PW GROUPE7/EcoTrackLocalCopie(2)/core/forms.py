from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Etudiant, Depense, Enqueteur

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Etudiant, Depense, Enqueteur

# Liste des quartiers étudiants de Yaoundé
QUARTIERS_YAOUNDE = [
    ('', '--- Sélectionnez un quartier ---'),
    ('Ngoa-Ekélé', 'Ngoa-Ekélé (Zone Universitaire)'),
    ('Briqueterie', 'Briqueterie'),
    ('Mvog-Mbi', 'Mvog-Mbi'),
    ('Mvog-Ada', 'Mvog-Ada'),
    ('Mvan', 'Mvan'),
    ('Efoulan', 'Efoulan'),
    ('Biyem-Assi', 'Biyem-Assi'),
    ('Melen', 'Melen'),
    ('Ekounou', 'Ekounou'),
    ('Obili', 'Obili'),
    ('Nkolbisson', 'Nkolbisson'),
    ('Nsimeyong', 'Nsimeyong'),
    ('Odza', 'Odza'),
    ('Ekoudou', 'Ekoudou'),
    ('Messassi', 'Messassi'),
    ('Mokolo', 'Mokolo'),
    ('Hippodrome', 'Hippodrome'),
    ('Mendong', 'Mendong'),
    ('Ahala', 'Ahala'),
    ('Nkol-Eton', 'Nkol-Eton'),
    ('Nkolmesseng', 'Nkolmesseng'),
    ('Cité Verte', 'Cité Verte'),
    ('Essos', 'Essos'),
    ('Bastos', 'Bastos'),
    ('Autre', 'Autre (préciser ci-dessous)'),
]

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matricule'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )

class EtudiantForm(forms.ModelForm):
    # Redéfinir le champ quartier pour utiliser une liste déroulante
    quartier = forms.ChoiceField(
        choices=QUARTIERS_YAOUNDE,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_quartier'
        })
    )
    
    # Champ optionnel pour préciser si "Autre" est sélectionné
    quartier_autre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Précisez le nom du quartier...',
            'id': 'id_quartier_autre',
            'style': 'display: none;'
        })
    )
    
    class Meta:
        model = Etudiant
        fields = [
            'code_enquete', 'nom', 'age', 'sexe', 'niveau', 
            'universite', 'quartier', 'quartier_autre', 'gps_lat', 'gps_lng', 'notes', 'photo'
        ]
        widgets = {
            'code_enquete': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: EC025_001'
            }),
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom complet de l\'étudiant'
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '16',
                'max': '35'
            }),
            'sexe': forms.Select(attrs={'class': 'form-select'}),
            'niveau': forms.Select(attrs={'class': 'form-select'}),
            'universite': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Université ou école'
            }),
            # NOTE: 'quartier' est redéfini au-dessus, ne pas le mettre ici
            'gps_lat': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Latitude (optionnel)'
            }),
            'gps_lng': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Longitude (optionnel)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': 'Observations pendant l\'enquête...'
            }),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si une instance existe, pré-remplir correctement
        if self.instance and self.instance.pk:
            quartier_value = self.instance.quartier
            
            # Vérifier si la valeur existe dans QUARTIERS_YAOUNDE
            quartier_in_list = any(quartier_value == value for value, _ in QUARTIERS_YAOUNDE[1:])  # [1:] pour sauter la première option vide
            
            if quartier_value and not quartier_in_list:
                # Si le quartier n'est pas dans la liste, c'est un "Autre"
                self.initial['quartier'] = 'Autre'
                self.initial['quartier_autre'] = quartier_value
                
                # Afficher le champ "autre"
                self.fields['quartier_autre'].widget.attrs['style'] = ''
    
    def clean(self):
        cleaned_data = super().clean()
        quartier = cleaned_data.get('quartier')
        quartier_autre = cleaned_data.get('quartier_autre')
        
        # Si "Autre" est sélectionné, utiliser la valeur de quartier_autre
        if quartier == 'Autre' and quartier_autre:
            cleaned_data['quartier'] = quartier_autre
        elif quartier == 'Autre' and not quartier_autre:
            self.add_error('quartier_autre', 'Veuillez préciser le nom du quartier')
        
        return cleaned_data

class DepenseForm(forms.ModelForm):
    # Redéfinir le champ quartier pour la dépense aussi
    quartier = forms.ChoiceField(
        choices=QUARTIERS_YAOUNDE,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_depense_quartier'
        })
    )
    
    # Champ optionnel pour préciser si "Autre" est sélectionné
    quartier_autre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Précisez le nom du quartier...',
            'id': 'id_depense_quartier_autre',
            'style': 'display: none;'
        })
    )
    
    class Meta:
        model = Depense
        fields = ['categorie', 'montant', 'quartier', 'quartier_autre', 'lieu_precis', 'date_depense', 'photo', 'commentaire']
        widgets = {
            'categorie': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '50',
                'placeholder': 'Montant en FCFA'
            }),
            # 'quartier' est redéfini au-dessus
            'lieu_precis': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom précis du lieu (marché, boutique, etc.)'
            }),
            'date_depense': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '2',
                'placeholder': 'Notes supplémentaires sur cette dépense'
            }),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Même logique que pour EtudiantForm
        if self.instance and self.instance.pk:
            quartier_value = self.instance.quartier
            quartier_in_list = any(quartier_value == value for value, _ in QUARTIERS_YAOUNDE[1:])
            
            if quartier_value and not quartier_in_list:
                self.initial['quartier'] = 'Autre'
                self.initial['quartier_autre'] = quartier_value
                self.fields['quartier_autre'].widget.attrs['style'] = ''
    
    def clean(self):
        cleaned_data = super().clean()
        quartier = cleaned_data.get('quartier')
        quartier_autre = cleaned_data.get('quartier_autre')
        
        if quartier == 'Autre' and quartier_autre:
            cleaned_data['quartier'] = quartier_autre
        elif quartier == 'Autre' and not quartier_autre:
            self.add_error('quartier_autre', 'Veuillez préciser le nom du quartier')
        
        return cleaned_data
