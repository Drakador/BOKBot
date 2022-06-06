from nextcord.ext import commands, tasks
import random
import logging
import datetime
import asyncpraw as praw

logging.basicConfig(level=logging.INFO)

client_id = ""
client_secret = ""


def load_client_data():
    try:
        global client_id
        global client_secret
        with open('Client.txt') as f:
            client_id = f.readline().strip('\n')
            client_secret = f.readline().strip('\n')
    except Exception as e:
        logging.error("Unable to load client data: " + str(e))


class Things(commands.Cog, name="Fun Things"):
    """For Fun/Event Type Things"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("Things cog loaded")
        load_client_data()
        self.scheduled_good_morning.start()

    @commands.command()
    async def lissa(self, ctx: commands.Context):
        """Lissa Does A Padme"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730138276855818/Lissa.gif')

    @commands.command()
    async def rng(self, ctx: commands.Context):
        """RNG In vAA HM"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730139770019921/RNG.gif')

    @commands.command()
    async def vundees(self, ctx: commands.Context):
        """Vundees Splooges"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730140604678204/Vundees.gif')

    @commands.command()
    async def fishing(self, ctx: commands.Context):
        """Glub Glub"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/976527850524016650/Fishing.gif')

    @commands.command()
    async def dance(self, ctx: commands.Context):
        """Jaeger does his thing"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730135919628328/Dance.gif')

    @commands.command()
    async def logz(self, ctx: commands.Context):
        """Actual gif of him"""
        await ctx.send("LISTEN HERE SHITHEADS!")
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730138935349308/Logz.gif')

    @commands.command()
    async def f(self, ctx: commands.Context):
        """F"""
        await ctx.send('https://tenor.com/view/keyboard-hyperx-rgb-hyperx-family-hyperx-gaming-gif-17743649')

    @commands.command()
    async def jabs(self, ctx: commands.Context):
        """The Templars do be like that"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/911837712196173824/jabs.gif')

    @commands.command()
    async def facepalm(self, ctx: commands.Context):
        """Arma every other second"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/912569604973404160/Facepalm.gif')

    @commands.command()
    async def hummus(self, ctx: commands.Context):
        """It's what Drak likes"""
        await ctx.send('https://tenor.com/view/hummus-hummusyes-hummushappy-gif-8630288')

    @commands.command()
    async def gabe(self, ctx: commands.Context):
        """Gabe did a thing"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/932432680178569276/Gabe.gif')

    @commands.command()
    async def maja(self, ctx: commands.Context):
        """How she be after we kick her butt"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/932433681992278088/Creed.gif')

    @commands.command()
    async def arty(self, ctx: commands.Context):
        """For Arty!"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/939988909352431666/For_Arty.gif')

    @commands.command()
    async def fly(self, ctx: commands.Context):
        """Pretty Fly for a Fly Guy"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/974769151774195733/Fly.gif')

    @commands.command()
    async def lost(self, ctx: commands.Context):
        """Then he was lost!"""
        await ctx.send('https://media.discordapp.net/attachments/911730032286785536/975825818506903562/Lost_died.gif')

    @commands.command()
    async def dungeons(self, ctx: commands.Context):
        """DUNGEONS"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/983363613425278997/dungeons.gif')

    @commands.command()
    async def youtube(self, ctx: commands.Context):
        """Links you to the BOK Trials Playlist"""
        await ctx.send('https://youtube.com/playlist?list=PL-z7L6gs44NMN_fDzsZY-3RRwaxHzxCBQ')

    @commands.command()
    async def lore(self, ctx: commands.Context):
        """Shows a random lore tidbit"""
        ran = random.randint(1, 10)  # Update to account for number of files
        grab = str(ran)
        grab += ".txt"
        with open('Lore/' + grab, ) as l:
            message = l.read()
        await ctx.send(message)

    @commands.command()
    async def joke(self, ctx: commands.Context):
        """Tells a Joke"""
        ran = random.randint(1, 11)  # Update to account for number of files
        grab = str(ran)
        grab += ".txt"
        with open('Jokes/' + grab, encoding="utf8") as l:
            message = l.read()
        await ctx.send(message)

    @commands.command()
    async def otter(self, ctx: commands.Context):
        """Adder"""
        await ctx.send('Adder')

    @commands.command()
    async def adder(self, ctx: commands.Context):
        """Otter"""
        await ctx.send('Otter')

    @commands.command()
    async def vka(self, ctx: commands.Context):
        """Something you wanna see for vKA"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/911837688141856768/congaline.png')

    @commands.command()
    async def lewd(self, ctx: commands.Context):
        """Be wary, very lewd option"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/911776421473550346/interlocking.gif')

    @commands.command()
    async def bokemon(self, ctx: commands.Context):
        """A link to a perfect song"""
        await ctx.send('https://youtu.be/OZrs7Blmank')

    @commands.command()
    async def thepull(self, ctx: commands.Context):
        """Drak got the thing"""
        await ctx.send('https://youtu.be/Cnf9lRtLSYk')

    @commands.command()
    async def fisted(self, ctx: commands.Context):
        """It happens to all of us"""
        await ctx.send(
            'https://media.discordapp.net/attachments/911730032286785536/932434215058944000/Slash_Fisted.PNG')

    @commands.command()
    async def chainz(self, ctx: commands.Context):
        """He always loses it"""
        await ctx.send('New phone who dis?')

    @commands.command()
    async def pizza(self, ctx: commands.Context):
        """Pizza Pizza"""
        await ctx.send('https://youtu.be/0YgW-05_y3A')

    @commands.command()
    async def rezparse(self, ctx: commands.Context):
        """When drak gets the highest rezzes instead of someone else"""
        await ctx.send('https://youtu.be/uRbLz8COzHg')

    @commands.command()
    async def philosophy(self, ctx: commands.Context):
        """The philosophy of Drak"""
        await ctx.send(
            "All Healers are soft mommy doms \nAll Tanks are masochists \nAll DPS are sadistic \n - Drak the Wise, "
            "who ponders his orb.")

    @commands.command()
    async def translate(self, ctx: commands.Context):
        """For the Boomers to understand Drak"""

        await ctx.send("Pog/Poggers: A triumphant cry of celebration. \nBased: The opposite of cringe. "
                       "\nRedpilled: To have seen reality for what it is. \nBaller: Very nice"
                       "\nNo Cap: An expression of authenticity."
                       "\nSussy Baka: An insincere comment saying summon is a suspicious fool, said as a joke."
                       "\nBussin: Same as Baller")

    @commands.command(name="twitch")
    async def get_twitch_url(self, ctx: commands.context):
        """Share Draks Twitch URL"""
        try:
            await ctx.send("https://www.twitch.tv/drakadorx")
        except Exception as e:
            await ctx.send("Unable to send link.")
            logging.error("Print Twitch Error: " + str(e))

    @commands.command(name="8ball")
    async def magic_eight_ball(self, ctx: commands.context):
        """Answers a question like a magic 8-ball"""
        # responses from here: https://en.wikipedia.org/wiki/Magic_8-ball#Possible_answers
        try:
            ran = random.randint(1, 20)
            response = ""
            match ran:
                case 1:
                    response = "It is certain."
                case 2:
                    response = "It is decidedly so."
                case 3:
                    response = "Without a doubt."
                case 4:
                    response = "Yes definitely."
                case 5:
                    response = "You may rely on it."
                case 6:
                    response = "As I see it, yes."
                case 7:
                    response = "Most likely."
                case 8:
                    response = "Outlook good."
                case 9:
                    response = "Yes."
                case 10:
                    response = "Signs point to yes."
                case 11:
                    response = "Reply hazy, try again."
                case 12:
                    response = "Ask again later."
                case 13:
                    response = "Better not tell you now."
                case 14:
                    response = "Cannot predict now."
                case 15:
                    response = "Concentrate and ask again."
                case 16:
                    response = "Don't count on it."
                case 17:
                    response = "My reply is no."
                case 18:
                    response = "My sources say no."
                case 19:
                    response = "Outlook not so good."
                case 20:
                    response = "Very doubtful. "
            if ran % 2 == 1:
                ran = random.randint(1, 10)  # Give this a like 1 in 10 chance of showing up if the number is odd
                if ran == 2:
                    response = "Fuck off I am sleeping."

            await ctx.reply(response)
        except Exception as e:
            await ctx.send("Unable to use the magic, something is blocking it!")
            logging.error("Magic 8 Ball Error: " + str(e))

    @commands.command()
    async def goodnight(self, ctx: commands.context):
        """A way to say goodnight to bok"""

        # Wow, this looks ugly, ah well. Say goodnight to the guildies
        message = """
In the great big room
There was a parse dummy backwards in the room
And a merchant buffoon.
And a picture of our first trial clear
And there were there were three little pvpers sitting on chairs
And two little kittens, and even two chickens
And even a Leah, asking for pizza at 1 AM
And a blacksmith and a clothier and a bowl full of alchemy
And a quiet old guild-mom who was whispering “hush”

Goodnight room
Goodnight moon
Goodnight parse dummy backwards in the room
Goodnight light
And the buffoon
Goodnight pvpers
Goodnight chairs
Goodnight kittens
And goodnight chickens
Goodnight clocks
And goodnight socks
Goodnight Leah
Goodnight blacksmith
And goodnight clothier
Goodnight nobody
Goodnight alchemy
And goodnight to the guild-mom whispering “hush”
Goodnight stars
Goodnight air
Goodnight noises everywhere
Goodnight BOK
"""
        await ctx.send(message)

    @commands.command()
    async def morning(self, ctx: commands.context):
        """A way to say good morning to bok"""
        await ctx.send('https://cdn.discordapp.com/attachments/911730032286785536/970733506948890655/sleepy-sleep.gif')

    @tasks.loop(time=datetime.time(13, 0, 0, 0))  # UTC Time, remember to convert and use a 24 hour-clock.
    async def scheduled_good_morning(self):
        channel = self.bot.get_guild(574095793414209556).get_channel(574095793414209558)
        await channel.send("Good Morning!")

    @commands.command()
    async def joined(self, ctx: commands.context):
        """Tells you when you joined the server"""
        try:
            user = ctx.message.author
            await ctx.reply(f"You, {user.display_name}, joined {ctx.guild.name} on {user.joined_at}")
        except Exception as e:
            logging.error("Joined command error: " + str(e))
            await ctx.send("Unable to fetch joined information.")

    @commands.command()
    async def azure(self, ctx: commands.context):
        """Something he said"""
        try:
            ran = random.randint(1, 5)
            match ran:
                case 1:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/974767389352804412/Azure.png')
                case 2:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/976489973937213480/nave.png')
                case 3:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/979226645271552040/Suck_Butt.png')
                case 4:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/978509287498350642/More_Azure.png')
                case 5:
                    await ctx.send("https://media.discordapp.net/attachments/911730032286785536/981993091202445322/unknown.png")
        except Exception as e:
            await ctx.send("Unable to send image")
            logging.error("Azure error: " + str(e))

    @commands.command()
    async def atios(self, ctx: commands.context):
        """His big secret ability"""
        try:
            ran = random.randint(1, 3)
            match ran:
                case 1:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/974855284772188200/Atios.png')
                case 2:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/974882271981088778/ctx_lissa.png')
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/974882282190037002/Share.gif')
                case 3:
                    await ctx.send("https://media.discordapp.net/attachments/911730032286785536/981757956511117322/unknown.png")
        except Exception as e:
            await ctx.send("Unable to send image")
            logging.error("Atios error: " + str(e))

    @commands.command()
    async def char(self, ctx: commands.context):
        """He got something"""
        try:
            await ctx.send('https://media.discordapp.net/attachments/911730032286785536/974767399981158500/Context.png')
        except Exception as e:
            await ctx.send("Unable to send image.")
            logging.error("Char error: " + str(e))

    @commands.command(name="gnight")
    async def goodnight_fly(self, ctx: commands.context):
        """Fly lives upside down."""
        try:
            await ctx.send("Goodnight Fly!")
        except Exception as e:
            await ctx.send("I cannot say goodnight!")
            logging.error("Gnight error: " + str(e))

    @commands.command(name="reddit")
    async def get_random_from_reddit(self, ctx: commands.context):
        """Gets a random copypasta from reddit."""
        try:
            global client_id
            global client_secret
            await ctx.send("Loading a random post...")
            reddit = praw.Reddit(client_id=client_id,
                                 client_secret=client_secret,
                                 user_agent='Linux:BOKBot:v2.0 by u/Drakidor')
            subreddit = await reddit.subreddit('elderscrollsonline')
            posts = [submission async for submission in subreddit.top()]
            ran = random.randint(1, len(posts))
            post = posts[ran]
            await ctx.send("A random hot post from r/elderscrollsonline for you!")
            await ctx.send(post.title)
            if post.url:
                await ctx.send(post.url)
            if post.selftext:
                await ctx.send(post.selftext)
            await ctx.send(f"https://www.reddit.com{post.permalink}")
        except Exception as e:
            await ctx.send("I was unable to complete the command.")
            logging.error("Reddit error: " + str(e))

    @commands.command(name="wrap")
    async def create_bubblewrap(self, ctx: commands.context):
        """For all your popping needs"""
        message = f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||\n"\
                  f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||\n"\
                  f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||\n"\
                  f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||"
        await ctx.send(message)

    @commands.command(name="arma")
    async def get_arma_moment(self, ctx: commands.Context):
        """Arma Moments"""
        try:
            ran = random.randint(1, 2)
            match ran:
                case 1:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730134044794930/Arma.gif')
                case 2:
                    await ctx.send('https://youtu.be/SQ9oCUNNbxc')
        except Exception as e:
            await ctx.send("Unable to send image")
            logging.error("Arma error: " + str(e))

    @commands.command(name="drak")
    async def get_drak_moment(self, ctx: commands.Context):
        """Drak Moments"""
        try:
            ran = random.randint(1, 2)
            match ran:
                case 1:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/911730136628461589/Drak.gif')
                case 2:
                    await ctx.send('https://media.discordapp.net/attachments/911730032286785536/982005217069498378/unknown.png')
        except Exception as e:
            await ctx.send("Unable to send image")
            logging.error("Drak error: " + str(e))

    @commands.command(name="abbr")
    async def dm_trial_abbreviations(self, ctx: commands.Context):
        """DMs the User the Trial abbreviations"""
        message = f"n - Normal\n" \
                  f"v - Veteran\n" \
                  f"+[#] - How many Minis are up for the Arena type Trials\n" \
                  f"hm - Hard Mode\n" \
                  f"hrc - Hel Ra Citadel\n" \
                  f"aa - Atherian Archive\n" \
                  f"so - Sanctum Ophidia\n" \
                  f"mol - Maw of Lorkhaj\n" \
                  f"hof - Halls of Fabrication\n" \
                  f"as - Asylum Sanctorium\n" \
                  f"cr - Cloud Rest\n" \
                  f"ss - Sunspire\n" \
                  f"ka - Kyne's Aegis\n" \
                  f"rg - Rockgrove\n" \
                  f"dsr - Dreadsail Reef"
        author = ctx.author
        await author.send(message)

    @commands.command(name="synn")
    async def synn_toes(self, ctx: commands.Context):
        """Sent these babies for free"""
        try:
            await ctx.send("https://cdn.discordapp.com/attachments/911730032286785536/983462009871937566/synn.gif")
        except Exception as e:
            await ctx.send("Unable to send gif")
            logging.error("Synn error: " + str(e))

    @commands.command(name="Klix")
    async def klixse(self, ctx: commands.Context):
        """Sometimes I wonder if anyone here is sane."""
        try:
            await ctx.send("https://media.discordapp.net/attachments/911730032286785536/983171690056024114/Klix.png")
        except Exception as e:
            await ctx.send("Unable to send image")
            logging.error("Klix error: " + str(e))

#    @tasks.loop(time=datetime.time(12, 0, 0, 0))
#    async def arma_reminder(self, bot):
#        """An automated task to remind Arma to do stuff"""
#        # Check if it is Monday at Noon
#        if datetime.today().weekday() == 0:
#            guild = bot.get_guild(id=574095793414209556)
#            arma = guild.get_member(152077378317844480)
#            if arma:
#                await arma.send("Reminder to go and look at Guild Traders")


def setup(bot: commands.Bot):
    bot.add_cog(Things(bot))
