import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
import traceback
import sys
import random
import itertools

with open("token.txt", "r") as f:
    token = f.read()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler_stream = logging.StreamHandler(sys.stdout)
handler_file = logging.FileHandler("logs.log", encoding="utf-8")
handler_stream.setFormatter(formatter)
handler_file.setFormatter(formatter)
logger.addHandler(handler_stream)
logger.addHandler(handler_file)

def logMessage(message: str, type="info", indent=False):
    """
    Renvoie un message de log dans le fichier log et la console.
    """
    if indent:
        message = "|-> " + message
    if type == "info":
        message = "\033[34m" + message + "\033[0m"
        logger.info(message)
    elif type == "warning" or "warn":
        message = "\033[33m" + message + "\033[0m"
        logger.warning(message)
    elif type == "error":
        message = "\033[31m" + message + "\033[0m"
        logger.error(message)
    elif type == "debug":
        logger.debug(message)
    elif type == "critical":
        message = "\033[41m" + message + "\033[0m"
        logger.critical(message)
    else:
        logMessage(f"[logMessage] Erreur : le type de log n'est pas reconnu : type={type}, type(type)={type(type)}, indent={indent}", type="error")

COULEURS: dict[str, tuple[str, str, str]] = {
    "B": ("Bleu", "#0000FF", "🔵"),
    "J": ("Jaune", "#FFFF00", "🟡"),
    "R": ("Rouge", "#FF0000", "🔴"),
    "V": ("Vert", "#00FF00", "🟢"),
}
COMBINAISON = None
DIFFICULTE = 6
DEVMODE = True

class Couleur():
    def __init__(self, nom: str, hex: str, emoji: str):
        self.nom = nom
        self.hex = hex
        self.emoji = emoji

class Lettre():
    def __init__(self, lettre: str):
        if type(lettre) is not str:
            raise TypeError(f"'lettre' doit être une string ('lettre' est de type {type(lettre)}).")

        self.nom = lettre if len(lettre) == 1 else None

        self.couleur: Couleur = Couleur(COULEURS[lettre][0], COULEURS[lettre][1], COULEURS[lettre][2])
        self.locked = False

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

class Combinaison():
    def __init__(self, comb: str):
        self.lettres: list[Lettre] = []
        for lettre in comb.upper():
            self.lettres.append(Lettre(lettre))

    def len(self) -> int:
        return len(self.lettres)

    def __str__(self) -> str:
        return self.lettres_str()
    
    def lettres_str(self) -> str:
        texte = ""
        for lettre in self.lettres:
            texte += lettre.nom if lettre.nom else "?"
        return texte
    
    def lettres_str_emojis(self) -> str:
        texte = ""
        for lettre in self.lettres:
            texte += lettre.couleur.emoji
        return lettre
 
class Partie():
    """
    Permet de gérer les parties.
    """
    def __init__(self, user_id: int, longueur: int, essais_max: int = 10):
        self.user_id = user_id
        self.longueur = longueur
        self.essais_max = essais_max
        self.combinaison_secrete = self.generer_combinaison() 
        self.essais = [] # non utilisé (à implémenter)
        self.essais_restants = self.essais_max
        self.termine = False

    def generer_combinaison(self) -> Combinaison:
        return Combinaison(''.join(random.choices(list(COULEURS.keys()), k=self.longueur)))

    def verifier(self, proposition: Combinaison | str) -> tuple[int, int] | None:
        """
        Renvoie le nombre de lettres bonnes et le nombre de lettres mauvaises.
        Renvoie None si la partie est terminée ou que la longeur de la combinaison donnée n'est pas bonne.
        """
        bien_places, mal_places = 0, 0

        if self.termine:
            return None
        
        if type(proposition) == str:
            proposition: Combinaison = Combinaison(proposition)
        
        if len(proposition.lettres) != self.longueur: # simple sécurité : on vérifie déjà la longueur dans le on_message
            print(len(proposition.lettres), self.longueur)
            return None

        secret = list(self.combinaison_secrete.lettres)
        props = list(proposition.lettres)
        utilisés_secret = [False] * len(secret)
        utilisés_prop = [False] * len(props)

        # Bien placés
        for i in range(len(secret)):
            if props[i].nom == secret[i].nom:
                bien_places += 1
                utilisés_secret[i] = True
                utilisés_prop[i] = True

        # Mal placés
        for i in range(len(props)):
            if utilisés_prop[i]:
                continue
            for j in range(len(secret)):
                if not utilisés_secret[j] and props[i].nom == secret[j].nom:
                    mal_places += 1
                    utilisés_secret[j] = True
                    break
        
        self.essais.append((proposition.lettres_str(), bien_places, mal_places))
        return bien_places, mal_places

class Resoudre():
    def __init__(self, combinaison: Combinaison | str | None):
        """
        Possibilité de donner une combinaison à résoudre. La combinaison est aléatoire si non spécifiée.
        """
        self.combinaison = combinaison if isinstance(combinaison, Combinaison) else Combinaison(combinaison) if isinstance(combinaison, str) else Combinaison(''.join(random.choices(list(COULEURS.keys()), k=DIFFICULTE)))
        self.essais = 0
        self.limite_essais = 10 # limite pour éviter boucles infinies
        self.essais_combs: list[tuple[str, int, int]] = []
    
    def comparer(self, essai: str) -> tuple[int, int]:
        """
        Compare un essai avec la combinaison cible et retourne (bien placés, mal placés)
        """
        secret = [l.nom for l in self.combinaison.lettres]
        props = list(essai)
        bien, mal = 0, 0
        utilisés_secret = [False] * len(secret)
        utilisés_prop = [False] * len(props)

        for i in range(len(secret)):
            if props[i] == secret[i]:
                bien += 1
                utilisés_secret[i] = True
                utilisés_prop[i] = True

        for i in range(len(props)):
            if utilisés_prop[i]:
                continue
            for j in range(len(secret)):
                if not utilisés_secret[j] and props[i] == secret[j]:
                    mal += 1
                    utilisés_secret[j] = True
                    break
        return bien, mal

    def filtre_valides(self, essais_possibles: list[str]) -> list[str]:
        """
        Filtre les combinaisons compatibles avec tous les retours précédents.
        """
        valides = []
        for comb in essais_possibles:
            ok = True
            for ancien_essai, ancien_bien, ancien_mal in self.essais_combs:
                bien, mal = self.simuler_comparaison(ancien_essai, comb)
                if bien != ancien_bien or mal != ancien_mal:
                    ok = False
                    break
            if ok:
                valides.append(comb)
        return valides

    def simuler_comparaison(self, essai: str, secret: str) -> tuple[int, int]:
        """
        Compare deux combinaisons (sous forme de str), sans modifier l'état.
        """
        bien, mal = 0, 0
        utilisés_secret = [False] * len(secret)
        utilisés_prop = [False] * len(essai)

        for i in range(len(secret)):
            if essai[i] == secret[i]:
                bien += 1
                utilisés_secret[i] = True
                utilisés_prop[i] = True

        for i in range(len(essai)):
            if utilisés_prop[i]:
                continue
            for j in range(len(secret)):
                if not utilisés_secret[j] and essai[i] == secret[j]:
                    mal += 1
                    utilisés_secret[j] = True
                    break
        return bien, mal

    def resoudre(self) -> tuple[Combinaison, int]:
        """
        Renvoie la combinaison trouvée et le nombre d'essais.
        """
        couleurs = list(COULEURS.keys())
        longueur = self.combinaison.len()
        essais_possibles = [''.join(p) for p in itertools.product(couleurs, repeat=longueur)]

        while self.essais < self.limite_essais and essais_possibles:
            tentative = essais_possibles[0]
            bien, mal = self.comparer(tentative)
            self.essais += 1
            self.essais_combs.append((tentative, bien, mal))

            if bien == longueur:
                return Combinaison(tentative), self.essais
            essais_possibles = self.filtre_valides(essais_possibles[1:])

        return Combinaison(tentative), self.essais

SESSIONS: dict[int, Partie] = {}

class Partie(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="jouer", description="Lance une partie de Partie")
    async def jouer(self, ctx: commands.Context):
        user_id = ctx.author.id

        # Nouvelle partie
        if user_id in SESSIONS.keys():
            ctx.send("Vous avez déjà une session de jeu en cours.")
            return
        
        SESSIONS[user_id] = Partie(user_id, DIFFICULTE)
        partie = SESSIONS[user_id]

        texte = f"""
        🎮 Partie lancée !\nDifficulté : {partie.longueur} lettres
        Vies restantes : {partie.essais_max}
        {'Combinaison (dev) : ' + partie.combinaison_secrete.lettres_str() if DEVMODE else ''}
        Répondez simplement avec une combinaison pour jouer (ex: BJRV)
        """
        await ctx.send(texte)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        partie = SESSIONS.get(user_id)
        if not partie:
            return
        
        if partie.termine:
            del SESSIONS[user_id]
            return

        prop_str = message.content.strip().upper()

        if len(prop_str) != partie.longueur:
            await message.channel.send(f"⛔ Votre combinaison doit contenir {partie.longueur} lettres.")
            return

        if any(l not in COULEURS for l in prop_str):
            await message.channel.send("⚠️ Utilisez uniquement les lettres suivantes : " + ', '.join(COULEURS.keys()))
            return

        try:
            prop = Combinaison(prop_str)
        except Exception:
            return

        bien, mal = partie.verifier(prop) if partie.verifier(prop) is not None else (None, None)
        if bien is None or mal is None:
            await message.channel.send(f"Une erreur s'est produite.")
            return 
        partie.essais_restants -= 1

        if bien == partie.longueur:
            await message.channel.send(f"🎉 Bravo {message.author.mention} ! Tu as trouvé la combinaison secrète : `{prop_str}`")
            partie.termine = True
            del SESSIONS[user_id]
            return

        if partie.essais_restants <= 0:
            await message.channel.send(f"💀 Partie terminée. Tu as perdu ! La combinaison était : `{partie.combinaison_secrete}`")
            partie.termine = True
            del SESSIONS[user_id]
            return

        await message.channel.send(f"🔍 Résultat : `{prop_str}`\n✔️ Bien placés : {bien}\n❌ Mal placés : {mal}\n❤️ Vies restantes : {partie.essais_restants}")

    @commands.hybrid_command(name="resoudre", description="Résout automatiquement une combinaison")
    async def resoudre(self, ctx: commands.Context, combinaison: str = None):
        await ctx.defer()
        await ctx.send(f"Veuillez patienter...")
        solveur = Resoudre(combinaison)
        solution, essais = solveur.resoudre()

        await ctx.send(f"Résolution automatique\nCombinaison cible : `{solveur.combinaison}`\nTrouvée : `{solution}`\nNombre d'essais : {essais} {'(limite atteinte)' if essais >= solveur.limite_essais else ''}")

    @commands.hybrid_command(name="difficulté", description="Change la difficulté")
    async def difficulté(self, ctx: commands.Context,  diff: int):
        global DIFFICULTE
        if not (1 <= diff <= 8):
            await ctx.send("La difficulté doit être comprise entre 1 et 8.")
        else:
            DIFFICULTE = diff
            texte = f"La difficulté a été changée en {diff}."
            if isinstance(COMBINAISON, Combinaison) and COMBINAISON.len() != DIFFICULTE:
                texte += "\nLa combinaison a été supprimée car elle ne remplit pas les nouvelles conditions de difficultés."
            await ctx.send(texte)

    @commands.hybrid_command(name="infos", description="Informations utiles")
    async def infos(self, ctx: commands.Context):
        texte = "## Informations :"
        texte += f"\nDifficulté : {DIFFICULTE}"
        texte = "## Liste des couleurs"
        for lettre, (coul, hex, emoji) in COULEURS.items():
            texte += f"\n{lettre} = {coul} : {emoji} ({hex})"
        texte += "\n\nCette commande n'affiche que les informations utiles, pour consulter l'aide relative aux commmandes, faites !help."
        await ctx.send(texte)

class Admin(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="eval", description="Évalue un instruction. (Admin)")
    async def admineval(self, ctx: commands.Context,  ins: str):
        if ctx.author.id != 453911322678263810 and not DEVMODE:
            await ctx.send("Le mode développeur n'est pas activé.")
            return
        
        try:
            await ctx.send(eval(ins), ephemeral=True)
        except Exception:
            await ctx.send(traceback.format_exc(), ephemeral=True)

    @commands.hybrid_command(name="enable", description="Active les commandes de développeur. (Admin)")
    async def admin(self, ctx: commands.Context):
        global DEVMODE
        if DEVMODE:
            DEVMODE = False
        else:
            DEVMODE = True
        await ctx.send(f"Le mode développeur a été {'' if DEVMODE else 'dés'}activé.")
    
    @commands.hybrid_command(name="stop", description="Arrête le bot.")
    async def stop(self, ctx: commands.Context):
        if ctx.author.id not in [453911322678263810, 428545486778007554]:
            await ctx.send(f"Vous n'avez pas la permission de faire cela.")
            return
        await ctx.send(f"Arrêt du bot.", ephemeral=True)
        await bot.close()

@bot.event
async def on_error(event, *args, **kwargs):
    logMessage(f"Une erreur s'est produite : {event}\n{traceback.format_exc()}", type="error")

@bot.event
async def on_app_command_error(ctx: commands.Context, error: app_commands.AppCommandError):
    logMessage(f"Une erreur est survenue lors de l'éxecution d'une commande : {error}\n{traceback.format_exc()}", type="error")
    await ctx.send(f"Une erreur est survenue lors de l'execution de la commmande : {error}")

@bot.event
async def on_ready():
    logMessage(f"Connecté en tant que '{bot.user}'")
    assert 1351462567230570556 in [guild.id for guild in bot.guilds], "Le bot ne se trouve pas sur le serveur de test."
    
    await bot.add_cog(Partie(bot))
    await bot.add_cog(Admin(bot))
    logMessage("Synchronisation terminée.")

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Partie"))
    logMessage("Bot prêt.")
    # logMessage(f"{[command.name for group in bot.tree._get_all_commands() for command in group.commands]}")

bot.run(token, reconnect=True)
