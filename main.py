import discord
from discord.ext import commands
import logging
import re
import random
import traceback

handler = logging.FileHandler(filename='discord.log',
                              encoding='utf-8',
                              mode='w')

with open("token.txt", "r") as f:
    token = f.read()

id_serveur = 1351462567230570556

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

COULEURS: dict[str, tuple[str, str, str]] = {
    "A": ("Azur", "#007FFF", "A"),
    "B": ("Bleu", "#0000FF", "🔵"),
    "C": ("Cyan", "#00FFFF", "C"),
    "E": ("Émeraude", "#00815F", "E"),
    "F": ("Framboise", "#C72C48", "F"),
    "G": ("Gris", "#AFAFAF", "G"),
    "H": ("Héliotrope", "#DF73FF", "H"),
    "I": ("Indigo", "#791CF8", "I"),
    "J": ("Jaune", "#FFFF00", "J"),
    "L": ("Lime", "#9EFD38", "L"),
    "M": ("Magenta", "#FF00FF", "M"),
    "N": ("Noir", "#FFFFFF", "⚫"),
    "O": ("Orange", "#CC5500", "🟠"),
    "P": ("Prune", "#811453", "P"),
    "R": ("Rouge", "#FF0000", "🔴"),
    "S": ("Saumon", "#F88E55", "S"),
    "T": ("Turquoise", "#25FDE9", "T"),
    "V": ("Vert", "#00FF00", "🟢"),
    "Z": ("Zinzolin", "#6C0277", "Z")
}
COMBINAISON = None
DIFFICULTE = 4
DEVMODE = False


class Couleur():

    def __init__(self, nom: str, hex: str, emoji: str):
        self.nom = nom
        self.hex = hex
        self.emoji = emoji


class Lettre():

    def __init__(self, lettre: str):
        if type(lettre) is not str:
            raise TypeError("lettre doit être une string.")

        self.nom = lettre if len(lettre) == 1 else None

        self.couleur: Couleur = Couleur(COULEURS[lettre][0],
                                        COULEURS[lettre][1], 
                                        COULEURS[lettre][2])
        self.locked = False

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False


class Combinaison():

    def __init__(self, comb: str):
        self.lettres: dict[str, Lettre] = {}
        if re.fullmatch(r"[A-Z]+", comb) and len(comb) == DIFFICULTE:
            for lettre in list(comb):
                self.lettres[lettre.upper()] = Lettre(lettre.upper())
        else:
            raise TypeError(f"Caractères invalides : {comb} et {[type(c) for c in comb]}")

    def len(self):
        return len(self.lettres)

    def __str__(self):
        return self.lettres_str()

    def lettres_str(self):
        texte = ""
        for lettre in self.lettres.values():
            texte += lettre.nom if lettre.nom else "?"
        return texte

    def lettres_emojis(self):
        return "".join(lettre.couleur.emoji for lettre in self.lettres.values())


class Partie():

    def __init__(self, combinaison: Combinaison):
        self.combinaison = combinaison

        self.essais = 0
        self.joueur = None

    def set_player(self, joueur: discord.Member | discord.User):
        if isinstance(joueur, (discord.Member, discord.User)):
            self.joueur = joueur
        else:
            raise TypeError("Le joueur n'est pas un membre")

    def check_combinaison(self, combinaison: str) -> bool:
        if len(combinaison) != len(self.combinaison.lettres):
            return False

        for lettre in combinaison:
            if lettre.upper() not in self.combinaison.lettres.keys():
                return False

        return True


class MastermindView(discord.ui.View):

    def __init__(self, ctx: commands.Context, partie: Partie):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.message = None
        self.partie = partie

        self.partie.set_player(ctx.author)

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "Vous n'êtes pas autorisé à utiliser cette interaction.",
                ephemeral=True)
            return False
        return True


@commands.command(name="set", help="Ajoute une combinaison à la liste")
async def set(ctx, combinaison: str):
    global COMBINAISON
    if combinaison == "random" or combinaison == "aléatoire":
        combinaison = ""
        for _ in range(DIFFICULTE):
            combinaison += random.choice(list(COULEURS.keys()))
    elif re.match(r"[A-Z]+", combinaison.upper()):
        if len(combinaison) != DIFFICULTE:
            await ctx.send(
                f"La combinaison doit contenir {DIFFICULTE} lettres.\nVous pouvez faire la commande !diffuclté pour changer le nombre de lettre."
            )
            return
        for lettre in list(combinaison):
            if lettre not in COULEURS.keys():
                await ctx.send(
                    f"La lettre {lettre} n'est pas une couleur valide.\nVous pouvez faire !couleurs pour voir les couleurs disponibles."
                )
                return
    else:
        await ctx.send("Erreur : la combinaison n'est pas valide.")

    COMBINAISON = Combinaison(combinaison)
    await ctx.send(
        f"La combinaison {combinaison} a été ajoutée aux combinaisons.")
    

@commands.command(name="reset", help="Supprime une combinaison de la liste")
async def reset(ctx, combinaison: str):
    global COMBINAISON
    COMBINAISON = None
    await ctx.send("Combinaison supprimée.")


@commands.command(name="resoudre",
                  help="Résout automatiquement une combinaison")
async def resoudre(ctx, combinaison: str):
    # algorithme à faire (sylvain)
    await ctx.send("Cette fonctionnalité n'est pas encore implémentée.")


@commands.command(name="couleurs", help="Affiche les couleurs disponibles")
async def couleurs(ctx):
    texte = "## Liste des couleurs"
    for lettre, (coul, hex, emoji) in COULEURS.items():
        texte += f"\n{lettre} = {coul} : {emoji} ({hex})"
    await ctx.send(texte)


@commands.command(name="combinaison", help="Affiche la combinaison")
async def combinaison(ctx):
    if not COMBINAISON:
        await ctx.send("Il n'y a pas de combinaison.")
        return

    await ctx.send(
        f"La combinaison actuellement enregistrée est : {COMBINAISON}")


@commands.command(name="jouer", help="Lance une partie")
async def jouer(ctx, comb: str | None = None):  # à faire
    global COMBINAISON
    await ctx.defer(thinking=True)
    embed = discord.Embed(title="Marstermind", color=discord.Color.blue())
    if comb:
        COMBINAISON = Combinaison(comb)
    else:
        if not COMBINAISON:
            await ctx.send("Aucune combinaison n'a été trouvée.\nVous devez utiliser la commande comme suit : `!jouer <combinaison>`")
            return

        
    combinaison: Combinaison = COMBINAISON
    embed.description = f"La combinaison est : {combinaison} (la combinaison est donnée pour les tests).\n\n"
    texte = ""
    for lettre in combinaison.lettres.values():
        texte += lettre.couleur.emoji

    await ctx.send(embed=embed, view=MastermindView(ctx, Partie(combinaison)))

@commands.command(name="difficulté", help="Change la difficulté")
async def difficulté(ctx, diff: int):
    global DIFFICULTE
    if not (1 <= diff <= 8):
        await ctx.send("La difficulté doit être comprise entre 1 et 8.")
    else:
        DIFFICULTE = diff
        texte = f"La difficulté a été changée en {diff}."
        if isinstance(COMBINAISON,
                      Combinaison) and COMBINAISON.len() != DIFFICULTE:
            texte += "\nLa combinaison a été supprimée car elle ne remplit pas les nouvelles conditions de difficultés."
        await ctx.send(texte)


@commands.command(name="infos", help="Informations utiles")
async def infos(ctx):
    texte = "## Informations :"
    texte += f"\nCombinaison : {COMBINAISON}"
    texte += f"\nDifficulté : {DIFFICULTE}"
    texte += "\n\nCette commande n'affiche que les informations utiles, pour consulter l'aide relative aux commmandes, faites !help."
    await ctx.send(texte)


@commands.command(name="admineval", help="Évalue un instruction. (Admin)")
async def admineval(ctx, ins: str):
    if not DEVMODE:
        await ctx.send("Le mode développeur n'est pas activé.")
        return
    try:
        await ctx.send(eval(ins), ephemeral=True)
    except Exception:
        await ctx.send(traceback.format_exc(), ephemeral=True)


@commands.command(name="admin",
                  help="Active les commandes de développeur. (Admin)")
async def admin(ctx):
    global DEVMODE
    if DEVMODE:
        DEVMODE = False
    else:
        DEVMODE = False
    await ctx.send(
        f"Le mode développeur a été {'' if DEVMODE else 'dés'}activé.")


@bot.event
async def on_ready():
    print(f"Connecté en tant que '{bot.user}'")
    bot.add_command(set)
    bot.add_command(reset)
    bot.add_command(resoudre)
    bot.add_command(couleurs)
    bot.add_command(combinaison)
    bot.add_command(jouer)
    bot.add_command(difficulté)
    bot.add_command(infos)
    bot.add_command(admineval)
    bot.add_command(admin)
    print("Bot prêt.")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing, name="Mastermind"))


bot.run(token, log_handler=handler)
