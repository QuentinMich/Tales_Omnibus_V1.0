from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from modelcluster.fields import ParentalKey
from wagtail.models import Page, Site
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.snippets.models import register_snippet

from core.blocks import BaseStreamBlock
from core.models import NavigationSettings
from core.polices import theme_utilise_google_fonts
from core.slugs import SlugAutomatiqueMixin


from encyclopedie.models import EncyclopedieIndexPage


# 1. MENTIONS LÉGALES : le texte légal est FIXE (dans le template), le client
#    ne remplit que ce qu'on ne peut pas deviner (qui édite, qui héberge).
#    Le reste s'insère tout seul : nom du site, adresse, page Contact, date.
class MentionsLegalesPage(SlugAutomatiqueMixin, Page):
    slug_fixe = "mentions-legales"  # = le lien du pied de page

    class Meta:
        verbose_name = "Mentions légales"
        verbose_name_plural = "Mentions légales"

    STATUTS = [
        ('particulier', "Particulier"),
        ('professionnel', "Professionnel (micro-entreprise, société…)"),
        ('association', "Association"),
    ]

    # --- Éditeur : la personne (ou structure) responsable du site ---
    editeur_nom = models.CharField(max_length=255, verbose_name="Nom ou raison sociale")
    editeur_statut = models.CharField(max_length=20, choices=STATUTS, default='particulier', verbose_name="Statut")
    editeur_adresse = models.TextField(
        blank=True, verbose_name="Adresse",
        help_text="Un particulier peut la laisser vide : elle doit alors être connue de l'hébergeur."
    )
    editeur_email = models.EmailField(verbose_name="Email de contact")
    siret = models.CharField(
        max_length=20, blank=True, verbose_name="SIRET / RNA",
        help_text="Obligatoire pour un professionnel (SIRET) ou une association (RNA)."
    )
    directeur_publication = models.CharField(
        max_length=255, blank=True, verbose_name="Directeur de la publication",
        help_text="Si vide, c'est l'éditeur."
    )

    # --- Hébergeur : obligatoire (loi pour la confiance dans l'économie numérique) ---
    hebergeur_nom = models.CharField(max_length=255, verbose_name="Nom de l'hébergeur")
    hebergeur_adresse = models.TextField(verbose_name="Adresse de l'hébergeur")
    hebergeur_contact = models.CharField(
        max_length=255, blank=True, verbose_name="Téléphone ou site de l'hébergeur"
    )

    # --- Parties libres ---
    credits = RichTextField(
        blank=True, features=['bold', 'italic', 'link', 'ul'],
        verbose_name="Crédits",
        help_text="Illustrations, cartes, polices, musiques… et leurs auteurs."
    )
    complement = RichTextField(
        blank=True, features=['h3', 'bold', 'italic', 'link', 'ul', 'ol'],
        verbose_name="Informations complémentaires",
        help_text="Ajouté à la fin, après les sections automatiques."
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('editeur_nom'),
            FieldPanel('editeur_statut'),
            FieldPanel('editeur_adresse'),
            FieldPanel('editeur_email'),
            FieldPanel('siret'),
            FieldPanel('directeur_publication'),
        ], heading="Éditeur du site"),
        MultiFieldPanel([
            FieldPanel('hebergeur_nom'),
            FieldPanel('hebergeur_adresse'),
            FieldPanel('hebergeur_contact'),
        ], heading="Hébergeur"),
        FieldPanel('credits'),
        FieldPanel('complement'),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []
    max_count = 1  # une seule page de mentions légales

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # Inserts automatiques : rien à retaper si le site change d'adresse
        # ou si la page Contact est renommée.
        accueil = Site.find_for_request(request).root_page.specific
        context['adresse_site'] = request.build_absolute_uri('/')
        context['page_contact'] = getattr(accueil, 'page_contact', None)
        # Le lecteur Twitch/YouTube de l'accueil dépose ses propres cookies :
        # on le signale seulement s'il est réellement affiché.
        noms = {'twitch': "Twitch", 'youtube': "YouTube"}
        lecteurs = getattr(accueil, 'stream_player', None) or []
        context['lecteur_live'] = next(
            (noms.get(bloc.value.get('plateforme'), "vidéo") for bloc in lecteurs), None
        )
        # Un thème qui charge ses polices chez Google transmet l'adresse IP du
        # visiteur à Google : on le dit. Après manage.py heberger_polices, le
        # thème n'appelle plus Google et la phrase disparaît toute seule.
        reglages = NavigationSettings.load(request_or_site=request)
        context['polices_google'] = theme_utilise_google_fonts(reglages.theme)
        # Mesure d'audience : signalée seulement si un compte GoatCounter est indiqué.
        context['statistiques'] = bool(reglages.goatcounter)
        return context


# 1 bis. Page UNIVERS : le MJ d'un côté, le monde qu'il a construit de l'autre
class UniversPage(SlugAutomatiqueMixin, Page):
    slug_fixe = "univers"

    class Meta:
        verbose_name = "Univers"

    # --- Partie MJ (carte du haut + grande image, wireframe) ---
    mj_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Photo du MJ ou logo"
    )
    mj_presentation = RichTextField(
        blank=True,
        features=['bold', 'italic', 'link', 'ol', 'ul'],
        verbose_name="Présentation du MJ",
        help_text="Qui tu es, comment tu mènes tes parties..."
    )

    # --- Partie Univers (le monde) ---
    # "intro" garde ce nom : l'accueil la reprend quand son accroche est vide.
    intro = models.TextField(
        blank=True,
        verbose_name="Accroche de l'univers",
        help_text="Quelques phrases pour donner envie. Reprise sur l'accueil."
    )
    body = StreamField(
        BaseStreamBlock(), use_json_field=True, blank=True,
        verbose_name="Présentation du monde",
        help_text="Histoire, géographie, ambiance... (texte, images, vidéos)"
    )

    parent_page_types = ['home.HomePage']
    subpage_types = []
    max_count = 1  # un seul univers par site

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('mj_image'),
            FieldPanel('mj_presentation'),
        ], heading="Le MJ"),
        MultiFieldPanel([
            FieldPanel('intro'),
            FieldPanel('body'),
        ], heading="L'univers"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # Le gros bouton "Explore mon univers" mène à l'encyclopédie
        context['encyclopedie'] = EncyclopedieIndexPage.objects.live().first()
        return context


# 2. Champs dynamiques du formulaire de contact
class ContactFormField(AbstractFormField):
    page = ParentalKey(
        'ContactPage',
        on_delete=models.CASCADE,
        related_name='form_fields'
    )


# 3. Modèle pour la page de contact
class ContactPage(SlugAutomatiqueMixin, AbstractEmailForm):
    slug_fixe = "contact"

    intro = RichTextField(blank=True, verbose_name="Texte de présentation")
    thank_you_text = RichTextField(blank=True, verbose_name="Message de confirmation")
    
    main_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name="Image d'illustration"
    )

    content_panels = AbstractEmailForm.content_panels + [
        FieldPanel('main_image'),
        FieldPanel('intro'),
        InlinePanel('form_fields', label="Champs du formulaire"),
        FieldPanel('thank_you_text'),
        MultiFieldPanel([
            FieldPanel('to_address', heading="Destinataire (Email)"),
            FieldPanel('from_address', heading="Expéditeur (Email)"),
            FieldPanel('subject', heading="Sujet du mail"),
        ], heading="Configuration de l'envoi d'e-mail"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['prestations'] = Prestation.objects.all()
        return context


# 4. PRESTATIONS : snippet (menu « Fragments » de l'admin).
#    Pas une page : une prestation n'a pas d'URL à elle, mais elle s'affiche
#    à deux endroits (page Contact + box Contact de l'accueil). Le client la
#    saisit une fois ; s'il n'en crée aucune, les sections ne s'affichent pas.
@register_snippet
class Prestation(models.Model):
    titre = models.CharField(max_length=100, verbose_name="Titre")
    description = RichTextField(
        blank=True,
        features=['bold', 'italic', 'link', 'ul'],
        verbose_name="Description"
    )
    prix = models.CharField(
        max_length=100, blank=True,
        verbose_name="Prix",
        help_text="Texte libre : « 30 € la séance », « Sur devis », « Gratuit »..."
    )
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre d'affichage",
        help_text="Les plus petits nombres s'affichent en premier."
    )

    panels = [
        FieldPanel('titre'),
        FieldPanel('description'),
        FieldPanel('prix'),
        FieldPanel('ordre'),
    ]

    class Meta:
        ordering = ['ordre', 'titre']
        verbose_name = "Prestation"
        verbose_name_plural = "Prestations"

    def __str__(self):
        return self.titre


# 4. ANNONCES : le « bulletin » de l'accueil, au-dessus du lecteur de live.
#    La prochaine session (avec compte à rebours) et les nouveautés du MJ.
#    Un FRAGMENT et pas une page : une annonce n'a pas besoin de sa propre
#    adresse, le MJ l'écrit en 30 secondes depuis « Organisation ».
#    Elles se RETIRENT TOUTES SEULES : une « prochaine session » restée en
#    ligne trois semaines après fait un site abandonné, et un MJ qui ne code
#    pas oubliera de faire le ménage.
@register_snippet
class Annonce(models.Model):
    SESSION, NOUVEAUTE, INFO = 'session', 'nouveaute', 'info'
    TYPES = [
        (SESSION, "Prochaine session"),
        (NOUVEAUTE, "Nouveauté"),
        (INFO, "Information"),
    ]
    # Une session reste affichée PENDANT qu'elle se joue (« En ce moment ! »)
    DUREE_D_UNE_SESSION = timedelta(hours=5)
    # Une nouveauté ou une info non épinglée disparaît au bout d'un mois
    DUREE_PAR_DEFAUT = timedelta(days=30)

    type_annonce = models.CharField(max_length=20, choices=TYPES, default=NOUVEAUTE,
                                    verbose_name="Type d'annonce")
    titre = models.CharField(max_length=120, verbose_name="Titre",
                             help_text="Ex. : « Session 12 : l'assaut de Fort-Sombre ».")
    texte = RichTextField(blank=True, features=['bold', 'italic', 'link'], verbose_name="Texte")
    date_session = models.DateTimeField(
        null=True, blank=True, verbose_name="Date et heure de la session",
        help_text="Pour une « Prochaine session » : sert au compte à rebours de l'accueil.",
    )
    ou_la_suivre = models.CharField(
        max_length=100, blank=True, verbose_name="Où la suivre",
        help_text="Ex. : « En direct sur Twitch », « Sur le Discord ».",
    )
    lien = models.URLField(blank=True, verbose_name="Lien", help_text="Un bouton vers ce lien (chaîne, Discord…).")
    publiee_le = models.DateTimeField(
        default=timezone.now, verbose_name="Afficher à partir du",
        help_text="Une date future : l'annonce attend ce moment pour apparaître.",
    )
    fin_d_affichage = models.DateTimeField(
        null=True, blank=True, verbose_name="Retirer le",
        help_text="Vide : retrait AUTOMATIQUE (après la session ; au bout de 30 jours pour les autres).",
    )
    epinglee = models.BooleanField(
        default=False, verbose_name="Épinglée",
        help_text="Passe en premier et ne se retire pas toute seule (sauf date « Retirer le »).",
    )

    panels = [
        FieldPanel('type_annonce'),
        FieldPanel('titre'),
        FieldPanel('texte'),
        MultiFieldPanel([
            FieldPanel('date_session'),
            FieldPanel('ou_la_suivre'),
        ], heading="Pour une prochaine session"),
        FieldPanel('lien'),
        MultiFieldPanel([
            FieldPanel('publiee_le'),
            FieldPanel('fin_d_affichage'),
            FieldPanel('epinglee'),
        ], heading="Affichage"),
    ]

    class Meta:
        ordering = ['-publiee_le']
        verbose_name = "Annonce"
        verbose_name_plural = "Annonces"

    def __str__(self):
        return self.titre

    def clean(self):
        super().clean()
        if self.type_annonce == self.SESSION and not self.date_session:
            raise ValidationError({'date_session': "Indique la date et l'heure de la session "
                                                   "(c'est elle qui fait le compte à rebours)."})

    @property
    def est_une_session(self):
        return self.type_annonce == self.SESSION and self.date_session is not None

    @property
    def fin_de_session(self):
        return self.date_session + self.DUREE_D_UNE_SESSION if self.est_une_session else None

    def retiree_le(self):
        """Le moment où l'annonce quitte l'accueil (None : jamais)."""
        if self.fin_d_affichage:
            return self.fin_d_affichage
        if self.est_une_session:
            return self.fin_de_session
        return None if self.epinglee else self.publiee_le + self.DUREE_PAR_DEFAUT

    def est_visible(self, maintenant):
        fin = self.retiree_le()
        return self.publiee_le <= maintenant and (fin is None or maintenant < fin)

    @classmethod
    def du_moment(cls, maintenant=None, combien=3):
        """
        Pour l'accueil : (la prochaine session, [les autres annonces]).
        La session la plus PROCHE est mise en avant ; les autres annonces
        (épinglées d'abord, puis les plus récentes) en petites cartes.
        Peu d'annonces en base : le tri se fait en Python, lisiblement.
        """
        maintenant = maintenant or timezone.now()
        visibles = [a for a in cls.objects.filter(publiee_le__lte=maintenant) if a.est_visible(maintenant)]
        sessions = sorted((a for a in visibles if a.est_une_session), key=lambda a: a.date_session)
        prochaine = sessions[0] if sessions else None
        autres = sorted((a for a in visibles if a is not prochaine),
                        key=lambda a: (not a.epinglee, -a.publiee_le.timestamp()))
        return prochaine, autres[:combien]
