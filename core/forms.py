from django import forms

from core.antispam import champ_piege

class HeroContactForm(forms.Form):
    nom = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={'placeholder': 'Votre nom / pseudo'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Votre adresse e-mail'})
    )
    raison = forms.ChoiceField(
        choices=[
            ('question', 'Question sur le personnage'),
            ('rp', 'Proposition de RP / Backstory'),
            ('autre', 'Autre'),
        ],
        label="Raison du message"
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Votre message...', 'rows': 4})
    )
    # Le pot de miel (core/antispam.py) : caché aux humains, rempli par les robots
    site_internet = champ_piege()
