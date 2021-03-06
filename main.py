import discord
from discord.ext import commands
from crawler import ImdbCrawler

TOKEN = open('token.txt', 'r').read().split('\n')[0].split()[0]

client = commands.Bot(command_prefix='$', help_command=None)



@client.event
async def on_ready():
    print('Bot is ready.')


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send('Comando não encontrado.')
    else:
        await ctx.send('Error: ' + str(error))

@client.command(aliases=['?', 'ajuda', 'comandos'])
async def help(ctx):
    description = '''
**Comandos:**
$help - Mostra os comandos disponíveis.
$URL - Retorna um filme de uma IMDb watchlist/chart ou um episódio de uma série.

URL pode ser um link de uma watchlist:
<https://www.imdb.com/user/urlemail/watchlist>
Pode ser um link de um chart:
<https://www.imdb.com/chart/top/>
Pode ser um link de uma série:
<https://www.imdb.com/title/tt1234567/>

Se for o link de uma série ainda pode receber um filtro de temporadas com (, e -):
$<https://www.imdb.com/title/tt1234567/> 1-5 -> Retorna os episódios da temporada 1 a 5.
$<https://www.imdb.com/title/tt1234567/> 1,5-10 -> Retorna os episódios da temporada 1 e das temporadas 5 a 10.'''

    embed=discord.Embed(title="Comandos",url="https://pastebin.com/U5Emcgfr", description=description,colour=discord.Color.green())
    await ctx.send(embed=embed)

@client.command(aliases=['url'])
async def URL(ctx, *, url):
    crawler = ImdbCrawler(url)
    lista = crawler.get_winner()
    desc=f'''
**Título**: {lista['title']}
**Gênero**: {lista['genre']}
**Duração**: {lista['length']}

**Plot**:
{lista['plot']}

**Cast**: {lista['cast']}

**Score**: {lista['score']}

**Créditos**: {lista['credits']}
'''
    emb=discord.Embed(title=lista['title'],url=lista['link'],description=desc,colour=discord.Color.green())
    emb.set_thumbnail(url=lista['image'])
    await ctx.send(embed=emb)

"""
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$upcase'):
        await message.channel.send(str(message.content).replace("$upcase","").upper())

    if message.content.startswith('$d'):
        await message.channel.send("dawda")
"""

client.run(TOKEN)
