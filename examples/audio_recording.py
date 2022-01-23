import os
import discord
from discord.commands import Option, ApplicationContext

bot = discord.Bot(debug_guilds=[...])
bot.connections = {}


@bot.command()
async def start(ctx: ApplicationContext, encoding: Option(str, choices=["mp3", "wav", "pcm", "ogg", "mka", "mkv", "mp4", "m4a",])):
    """
    Record your voice!
    """

    voice = ctx.author.voice

    if not voice:
        return await ctx.respond("You're not in a vc right now")

    vc = await voice.channel.connect()
    bot.connections.update({ctx.guild.id: vc})

    if encoding == "mp3":
        sink = discord.sinks.MP4Sink()
    elif encoding == "wav":
        sink = discord.sinks.WaveSink()
    elif encoding == "pcm":
        sink = discord.sinks.PCMSink()
    elif encoding == "ogg":
        sink = discord.sinks.OGGSink()
    elif encoding == "mka":
        sink = discord.sinks.MKASink()
    elif encoding == "mkv":
        sink = discord.sinks.MKVSink()
    elif encoding == "mp4":
        sink = discord.sinks.MP4Sink()
    elif encoding == "m4a":
        sink = discord.sinks.M4ASink()

    vc.start_recording(
        sink,
        finished_callback,
        ctx.channel,
    )
    
    await ctx.respond("The recording has started!")


async def finished_callback(sink, channel: discord.TextChannel, *args):

    recorded_users = [
        f" <@{user_id}> ({os.path.split(audio.file)[1]}) "
        for user_id, audio in sink.audio_data.items()
    ]
    await sink.vc.disconnect()
    files = sink.get_all_audio()
    await channel.send(f"Finished! Recorded audio for {', '.join(recorded_users)}.", files=files)

@bot.command()
async def stop(ctx):
    """
    Stop recording.
    """
    if ctx.guild.id in bot.connections:
        vc = bot.connections[ctx.guild.id]
        vc.stop_recording()
        del bot.connections[ctx.guild.id]
        await ctx.delete()
    else:
        await ctx.respond("Not recording in this guild.")


bot.run("TOKEN")