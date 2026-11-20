from datetime import timedelta

from django.core import mail
from django.test import TestCase
from home.models import HomePage

from pages.models import ContactFormField, ContactPage


class ContactPageTests(TestCase):
    def setUp(self):
        home = HomePage.objects.first()
        self.contact = home.add_child(instance=ContactPage(
            title="Contact", slug="contact-test",
            to_address="moi@example.com", from_address="site@example.com",
            subject="Nouveau message",
        ))
        for i, (label, field_type) in enumerate([('Nom', 'singleline'), ('Email', 'email'), ('Message', 'multiline')]):
            ContactFormField.objects.create(page=self.contact, sort_order=i, label=label,
                                            field_type=field_type, required=True)

    def test_la_page_affiche_les_champs(self):
        response = self.client.get(self.contact.url)
        self.assertContains(response, 'form-group--nom')
        # Le textarea reçoit la classe qui le place dans la colonne de droite
        self.assertContains(response, 'form-group--message')

    def test_envoi_affiche_la_page_de_remerciement(self):
        response = self.client.post(self.contact.url, {
            'nom': "Alice", 'email': "alice@example.com", 'message': "Coucou",
        })
        self.assertTemplateUsed(response, 'pages/contact_page_landing.html')
        self.assertContains(response, "Message envoyé !")
        self.assertContains(response, 'panel--accent')  # même mise en page que la page contact
        self.assertEqual(len(mail.outbox), 1)


class PrestationsTests(TestCase):
    def setUp(self):
        from pages.models import Prestation
        self.home = HomePage.objects.first()
        self.contact = self.home.add_child(instance=ContactPage(title="Contact", slug="contact-presta"))
        self.home.page_contact = self.contact
        self.home.save_revision().publish()
        self.Prestation = Prestation

    def test_pas_de_prestation_pas_de_section(self):
        self.assertNotContains(self.client.get(self.contact.url), "Mes prestations")

    def test_page_contact_detail_et_ordre(self):
        self.Prestation.objects.create(titre="One-shot", prix="Sur devis", ordre=2)
        self.Prestation.objects.create(titre="Campagne", description="<p>Dix séances</p>", ordre=1)
        html = self.client.get(self.contact.url).content.decode()
        self.assertIn("Dix séances", html)  # description visible sur la page Contact
        self.assertLess(html.index("Campagne"), html.index("One-shot"))  # ordre respecté

    def test_accueil_version_courte(self):
        self.Prestation.objects.create(titre="Initiation", description="<p>Détail long</p>", prix="Gratuit")
        response = self.client.get(self.home.url)
        self.assertContains(response, "Initiation")
        self.assertContains(response, "Gratuit")
        self.assertNotContains(response, "Détail long")  # le détail reste sur la page Contact


class MentionsLegalesTests(TestCase):
    def setUp(self):
        from pages.models import MentionsLegalesPage
        self.home = HomePage.objects.first()
        self.page = self.home.add_child(instance=MentionsLegalesPage(
            title="Mentions légales",
            editeur_nom="Jean Conteur", editeur_email="jean@example.com",
            hebergeur_nom="Hébergeur SAS", hebergeur_adresse="1 rue du Serveur, Paris",
        ))
        # Publiée comme dans l'admin : c'est ce qui date la « dernière mise à jour »
        self.page.save_revision().publish()

    def test_slug_fixe_et_lien_dans_le_pied_de_page(self):
        self.assertEqual(self.page.slug, "mentions-legales")
        self.assertContains(self.client.get(self.home.url), 'href="/mentions-legales/"')

    def test_inserts_automatiques(self):
        html = self.client.get(self.page.url).content.decode()
        self.assertIn("Jean Conteur", html)
        self.assertIn("http://testserver/", html)  # adresse du site, déduite de la requête
        self.assertIn("Directeur de la publication : Jean Conteur", html)  # défaut = l'éditeur
        self.assertIn("Dernière mise à jour", html)
        self.assertNotIn("SIRET", html)  # vide : la ligne n'apparaît pas

    def test_lien_vers_la_page_contact(self):
        contact = self.home.add_child(instance=ContactPage(title="Écris-moi", slug="x"))
        self.home.page_contact = contact
        self.home.save_revision().publish()
        self.assertContains(self.client.get(self.page.url), "page Écris-moi")

    def test_cookies_du_lecteur_live_signales_seulement_s_il_existe(self):
        self.assertNotContains(self.client.get(self.page.url), "intègre un lecteur")
        self.home.stream_player = [('lecteur', {'plateforme': 'youtube', 'chaine': 'UC' + 'a' * 22, 'titre': ''})]
        self.home.save_revision().publish()
        self.assertContains(self.client.get(self.page.url), "intègre un lecteur YouTube")

    def test_mesure_d_audience_signalee_seulement_si_un_compte_est_indique(self):
        from core.models import NavigationSettings
        self.assertNotContains(self.client.get(self.page.url), "GoatCounter")
        reglages = NavigationSettings.load()
        reglages.goatcounter = "monunivers"
        reglages.save()
        self.assertContains(self.client.get(self.page.url), "<h2>Mesure d'audience</h2>", html=False)

    def test_une_seule_page_de_mentions(self):
        from pages.models import MentionsLegalesPage
        self.assertFalse(MentionsLegalesPage.can_create_at(self.home))


class AnnoncesTests(TestCase):
    """Le bulletin de l'accueil : prochaine session (compte à rebours) et annonces."""

    def setUp(self):
        from django.utils import timezone
        self.maintenant = timezone.now()

    def annonce(self, **champs):
        from pages.models import Annonce
        champs.setdefault('titre', "Annonce")
        champs.setdefault('publiee_le', self.maintenant)
        return Annonce.objects.create(**champs)

    def du_moment(self, decalage=None):
        from pages.models import Annonce
        return Annonce.du_moment(self.maintenant + (decalage or timedelta()))

    def test_la_session_la_plus_proche_est_mise_en_avant(self):
        loin = self.annonce(type_annonce='session', titre="Session 14", date_session=self.maintenant + timedelta(days=9))
        proche = self.annonce(type_annonce='session', titre="Session 13", date_session=self.maintenant + timedelta(days=2))
        prochaine, autres = self.du_moment()
        self.assertEqual(prochaine, proche)
        self.assertEqual(autres, [loin])  # l'autre session reste en petite carte

    def test_une_session_reste_pendant_qu_elle_se_joue_puis_disparait(self):
        self.annonce(type_annonce='session', date_session=self.maintenant + timedelta(hours=1))
        self.assertIsNotNone(self.du_moment(timedelta(hours=3))[0])   # en cours (« En ce moment ! »)
        self.assertIsNone(self.du_moment(timedelta(hours=7))[0])      # finie : retirée toute seule

    def test_une_nouveaute_se_retire_au_bout_de_30_jours_sauf_si_epinglee(self):
        self.annonce(titre="Nouvelle carte")
        self.annonce(titre="Règles de la table", epinglee=True)
        self.assertEqual([a.titre for a in self.du_moment()[1]], ["Règles de la table", "Nouvelle carte"])
        self.assertEqual([a.titre for a in self.du_moment(timedelta(days=31))[1]], ["Règles de la table"])

    def test_une_annonce_programmee_attend_sa_date(self):
        self.annonce(titre="Surprise", publiee_le=self.maintenant + timedelta(days=1))
        self.assertEqual(self.du_moment()[1], [])
        self.assertEqual(len(self.du_moment(timedelta(days=2))[1]), 1)

    def test_retirer_le_passe_avant_tout(self):
        self.annonce(titre="Courte", epinglee=True, fin_d_affichage=self.maintenant + timedelta(days=1))
        self.assertEqual(self.du_moment(timedelta(days=2))[1], [])

    def test_une_session_sans_date_est_refusee(self):
        from django.core.exceptions import ValidationError
        from pages.models import Annonce
        with self.assertRaises(ValidationError):
            Annonce(titre="Session ?", type_annonce='session').full_clean()

    def test_sur_l_accueil(self):
        from home.models import HomePage
        accueil = HomePage.objects.first()
        self.assertNotContains(self.client.get(accueil.url), "home-annonces")  # rien : pas de cadre vide
        self.annonce(type_annonce='session', titre="L'assaut", date_session=self.maintenant + timedelta(days=3),
                     ou_la_suivre="En direct sur Twitch")
        html = self.client.get(accueil.url).content.decode()
        self.assertIn("L&#x27;assaut", html)
        self.assertIn("data-compte-a-rebours=", html)
        self.assertIn("compte_a_rebours.js", html)
        self.assertIn("En direct sur Twitch", html)
