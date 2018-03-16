# Game made by GR8 from Legend Family.

import discord
from discord.ext import commands
from cogs.utils import checks
from .utils.dataIO import dataIO, fileIO
from collections import Counter, defaultdict, namedtuple
from .utils.chat_formatting import box
from __main__ import send_cmd_help
import os
from copy import deepcopy
import asyncio
import random
import operator

default_settings = {"CHANNEL": "381338442543398912", "CREDITS": 50, "ROLE": None, "LOCK": False, "QUESTIONS" : 60}
settings_path = "data/challenges/settings.json"
creditIcon = "https://i.imgur.com/TP8GXZb.png"
credits = "Bot by GR8 | Titan"

TriviaLine = namedtuple("TriviaLine", "question answers")

class challenges:
    """My custom cog that does stuff!"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(settings_path)
        self.active = False

    def add_defualt_settings(self, server):
        if server.id not in self.settings:
            self.settings[server.id] = deepcopy(default_settings)
            dataIO.save_json(settings_path, self.settings)

    def get_game_channel(self, server):
        try:
            return server.get_channel(self.settings[server.id]["CHANNEL"])
        except:
            return None

    def verify_role(self, server, role_name):
        """Verify the role exist on the server"""
        role = discord.utils.get(server.roles, name=role_name)
        return role is not None

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def chalset(self, ctx):
        """Sets Challenges settings"""
        server = ctx.message.server
        self.add_defualt_settings(server)

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @chalset.command(pass_context=True)
    async def channel(self, ctx, channel : discord.Channel):
        """Sets the channel to play challenges.

        If channel isn't specified, the server's default channel will be used"""
        server = ctx.message.server
        self.add_defualt_settings(server)

        if channel is None:
            channel = ctx.message.server.default_channel
        if not server.get_member(self.bot.user.id
                                 ).permissions_in(channel).send_messages:
            await self.bot.say("I do not have permissions to send "
                               "messages to {0.mention}".format(channel))
            return
        self.settings[server.id]["CHANNEL"] = channel.id
        dataIO.save_json(settings_path, self.settings)
        channel = self.get_game_channel(server)
        await self.bot.send_message(channel, "I will now use {0.mention} to start challenges".format(channel))

    @chalset.command(pass_context=True)
    async def credits(self, ctx, num):
        """Set credits you get per correct answer."""
        server = ctx.message.server
        self.add_defualt_settings(server)

        self.settings[server.id]["CREDITS"] = int(num)
        await self.bot.say("Credits per answer has been set to {}.".format(num))
        dataIO.save_json(settings_path, self.settings)

    @chalset.command(pass_context=True)
    async def role(self, ctx, role):
        """Set role you would like to mention when a challenge starts"""
        server = ctx.message.server
        self.add_defualt_settings(server)

        if not self.verify_role(server, role):
            await self.bot.say("{} is not a valid role on this server.".format(actor_role))
            return

        self.settings[server.id]["ROLE"] = role
        await self.bot.say("Mentionable role has been set to {}.".format(role))
        dataIO.save_json(settings_path, self.settings)

    @chalset.command(pass_context=True)
    async def channellock(self, ctx):
        """Lock channel when challenge starts"""
        server = ctx.message.server
        self.add_defualt_settings(server)

        self.settings[server.id]["LOCK"] = not self.settings[server.id]["LOCK"]
        await self.bot.say("Challenge lock set to {}.".format(str(self.settings[server.id]["LOCK"])))
        dataIO.save_json(settings_path, self.settings)

    @chalset.command(pass_context=True)
    async def questions(self, ctx, num):
        """Set number of questions per challenge"""
        server = ctx.message.server
        self.add_defualt_settings(server)

        self.settings[server.id]["QUESTIONS"] = int(num)
        await self.bot.say("questions per challenge has been set to {}.".format(num))
        dataIO.save_json(settings_path, self.settings)

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def chal(self, ctx):
        """Challenge Controls"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @chal.command(pass_context=True)
    async def start(self, ctx):
        """Start the challenge on the specified channel"""
        server = ctx.message.server
        self.add_defualt_settings(server)

        channel = self.get_game_channel(server)
        role_name = self.settings[server.id]["ROLE"]
        lock_state = self.settings[server.id]["LOCK"] 
        q_num = self.settings[server.id]["QUESTIONS"]
        delay = 60

        if self.active:
            await self.bot.say("A challenge is already running, wait for it to end first.")
            return

        if channel is None:
            await self.bot.say("Challenge channel not set, use ``[p]chalset channel`` to set your channel.")
            return

        if role_name is not None:
            challenges_role = discord.utils.get(server.roles, name=role_name)
            if challenges_role is None:
                await self.bot.create_role(server, name=role_name)
                challenges_role = discord.utils.get(server.roles, name=role_name)

            await self.bot.edit_role(server, challenges_role, mentionable=True)
            await self.bot.send_message(channel, ":rotating_light: New challenge starting in {} seconds :rotating_light: {}".format(str(delay), challenges_role.mention))
            await self.bot.edit_role(server, challenges_role, mentionable=False)
        else:
            await self.bot.send_message(channel, ":rotating_light: New challenge starting in {} seconds :rotating_light:".format(str(delay)))

        if lock_state:
            perm = discord.PermissionOverwrite(send_messages = False, read_messages = False)
            await self.bot.edit_channel_permissions(channel, server.default_role, perm)

        self.active = True

        await asyncio.sleep(delay)

        if lock_state:
            perm = discord.PermissionOverwrite(send_messages = None, read_messages = False)
            await self.bot.edit_channel_permissions(channel, server.default_role, perm)

        c = challengeSession(self.bot)
        await c.start_game(server)

        self.active = False

    @chal.command(pass_context=True)
    async def stop(self, ctx):
        """Stop the challenge on the specified channel"""
        server = ctx.message.server

        await self.bot.say("Challenge stopped.")
        self.active = False

class challengeSession():
    def __init__(self, bot):
        self.bot = bot
        self.games = 0
        self.settings = dataIO.load_json(settings_path)
        self.emoji = dataIO.load_json("data/challenges/emoji.json")
        self.words = dataIO.load_json("data/challenges/words.json")
        self.bank = self.bot.get_cog('Economy').bank
        self.scores = Counter()
        
    def get_game_channel(self, server):
        try:
            return server.get_channel(self.settings[server.id]["CHANNEL"])
        except:
            return None

    def parse_trivia_list(self, filename):
        path = "data/trivia/{}.txt".format(filename)
        parsed_list = []

        with open(path, "rb") as f:
            try:
                encoding = chardet.detect(f.read())["encoding"]
            except:
                encoding = "ISO-8859-1"

        with open(path, "r", encoding=encoding) as f:
            trivia_list = f.readlines()

        for line in trivia_list:
            if "`" not in line:
                continue
            line = line.replace("\n", "")
            line = line.split("`")
            question = line[0]
            answers = []
            for l in line[1:]:
                answers.append(l.strip())
            if len(line) >= 2 and question and answers:
                line = TriviaLine(question=question, answers=answers)
                parsed_list.append(line)

        if not parsed_list:
            raise ValueError("Empty trivia list")

        return parsed_list

    async def send_table(self):
        t = "+ Results: \n\n"
        for user, score in self.scores.most_common():
            t += "+ {}\t{}\n".format(user, score)
        await self.bot.say(box(t, lang="diff"))

    async def start_game(self, server):
        q_num = self.settings[server.id]["QUESTIONS"]

        if self is self.bot.get_cog("challenges"):
            return

        if self.games < q_num:
            gameList = [
                self.emoji_reacter,
                self.word_scramble,
                self.trivia,
                self.maths
            ]
            await random.choice(gameList)(server)
        else:
            await self.bot.say("Thats it, challenge ended. Type ``!togglerole challenges`` to get notified on the next challenge.")
            if self.scores:
                await self.send_table()

    async def emoji_reacter(self, server):
        channel = self.get_game_channel(server)
        
        emoji = random.choice(self.emoji)

        embed=discord.Embed(title=emoji['emoji'], description=emoji['description'], color=0x008000)
        embed.set_author(name="React with Emoji")
        embed.set_footer(text=credits, icon_url=creditIcon)

        msg = await self.bot.send_message(channel, embed=embed)

        def check(reaction, user):
            e = str(reaction.emoji)
            return e.startswith(emoji['emoji'])

        while True:
            react = await self.bot.wait_for_reaction(check=check, timeout=15)

            if react is None:
                break

            if react.user != self.bot.user:
                if react.reaction.emoji == emoji['emoji']:
                    try:
                        self.bank.deposit_credits(react.user, self.settings[server.id]["CREDITS"])
                        await self.bot.say("You got it {} (+{} credits)".format(react.user.mention, self.settings[server.id]["CREDITS"]))
                    except:
                        await self.bot.say("{} You dont have a bank account, please do ``!bank register``".format(react.user.mention)) 
                    self.scores[react.user] += 1
                    break

        await asyncio.sleep(3)

        self.games += 1
        await self.start_game(server)

    async def word_scramble(self, server):
        channel = self.get_game_channel(server)

        def scramble(word):
            foo = list(word)
            random.shuffle(foo)
            return ''.join(foo)
                
        word = random.choice(self.words)
        self.words.remove(word)

        embed=discord.Embed(title="", description=scramble(word).upper(), color=0x8000ff)
        embed.set_author(name="Unscramble the word")
        embed.set_footer(text=credits, icon_url=creditIcon)

        msg = await self.bot.send_message(channel, embed=embed)

        def check(msg):
            return word in msg.content.lower()

        while True:
            answer = await self.bot.wait_for_message(check=check, timeout=15)

            if answer is None:
                await self.bot.say("Time's up, it was **{}**".format(word))
                break 

            try:
                self.bank.deposit_credits(answer.author, self.settings[server.id]["CREDITS"])
                await self.bot.say("You got it {} (+{} credits)".format(answer.author.mention, self.settings[server.id]["CREDITS"]))
            except:
                await self.bot.say("{} You dont have a bank account, please do ``!bank register``".format(answer.author.mention))
            self.scores[answer.author] += 1
            break

        await asyncio.sleep(3)

        self.games += 1
        await self.start_game(server)

    async def trivia(self, server):
        channel = self.get_game_channel(server)

        trivia_list = random.choice(['artandliterature', 'clashroyale', 'computers', 'elements', 'games', 'general', 'uscapitals', 'worldcapitals'])     
        question_list = self.parse_trivia_list(trivia_list)        
        current_line = random.choice(question_list)
        question_list.remove(current_line)

        embed=discord.Embed(title="", description=current_line.question, color=0xff8000)
        embed.set_author(name="Answer the question")
        embed.set_footer(text=credits, icon_url=creditIcon)

        msg = await self.bot.send_message(channel, embed=embed)

        def check(msg):
            for answer in current_line.answers:
                answer = answer.lower()
                guess = msg.content.lower()
                if " " not in answer:
                    guess = guess.split(" ")
                    for word in guess:
                        if word == answer:
                            return True
                else:
                    if answer in guess:
                        return True
            return False

        while True:
            guess = await self.bot.wait_for_message(check=check, timeout=15)

            if guess is None:
                await self.bot.say("Time's up, it was **{}**".format(current_line.answers[0]))
                break

            try:
                self.bank.deposit_credits(guess.author, self.settings[server.id]["CREDITS"])
                await self.bot.say("You got it {} (+{} credits)".format(guess.author.mention, self.settings[server.id]["CREDITS"]))
            except:
                await self.bot.say("{} You dont have a bank account, please do ``!bank register``".format(guess.author.mention))
            self.scores[guess.author] += 1
            break

        await asyncio.sleep(3)

        self.games += 1
        await self.start_game(server)

    async def maths(self, server):
        channel = self.get_game_channel(server)

        ops = {'+':operator.add,
               '-':operator.sub,
               '*':operator.mul}
        num1 = random.randint(0,1200)
        num2 = random.randint(1,1000)
        op = random.choice(list(ops.keys()))
        number = ops.get(op)(num1,num2)

        embed=discord.Embed(title="", description='What is {} {} {}?\n'.format(num1, op, num2), color=0xff8080)
        embed.set_author(name="Calculate")
        embed.set_footer(text=credits, icon_url=creditIcon)

        msg = await self.bot.send_message(channel, embed=embed)

        def check(msg):
            return str(number) in msg.content.lower()

        while True:
            answer = await self.bot.wait_for_message(check=check, timeout=15)

            if answer is None:
                await self.bot.say("Time's up, the correct answer is **{}**".format(str(number)))
                break 

            try:
                self.bank.deposit_credits(answer.author, self.settings[server.id]["CREDITS"])
                await self.bot.say("You got it {} (+{} credits)".format(answer.author.mention, self.settings[server.id]["CREDITS"]))
            except:
                await self.bot.say("{} You dont have a bank account, please do ``!bank register``".format(answer.author.mention))
            self.scores[answer.author] += 1
            break

        await asyncio.sleep(3)

        self.games += 1
        await self.start_game(server)

def check_folders():
    if not os.path.exists("data/challenges"):
        print("Creating data/challenges folder...")
        os.makedirs("data/challenges")

def check_files():
    f = settings_path
    if not dataIO.is_valid_json(f):
        print("Creating challenges settings.json...")
        dataIO.save_json(f, {})
    else:  # consistency check
        current = dataIO.load_json(f)
        for k, v in current.items():
            if v.keys() != default_settings.keys():
                for key in default_settings.keys():
                    if key not in v.keys():
                        current[k][key] = deepcopy(default_settings)[key]
                        print("Adding " + str(key) +
                              " field to challenges settings.json")

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(challenges(bot))