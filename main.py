import asyncio
import discord
from discord.ext import commands
from twilio.rest import Client
import random
import websockets
import json
import base64
import config
from wake_word import WakeWordDetector
from speech_recognition import SpeechRecognizer
from audio_bridge import AudioBridge, DiscordAudioHandler
import database
import tts

active_bridges = {}
current_calls = 0
ws_server = None

twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def has_permission(ctx):
    if not ctx.author.guild_permissions.administrator:
        roles = [role.name for role in ctx.author.roles]
        if not any(role in config.ALLOWED_ROLES for role in roles):
            return False
    return True

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await database.init_db()

@bot.command()
@commands.check(has_permission)
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send("You are not in a voice channel.")
        return
    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send(f"Joined {channel.name}")
    await start_command_listening(ctx.voice_client, str(ctx.channel.id), str(ctx.author.id))

@bot.command()
@commands.check(has_permission)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Left voice channel")
    else:
        await ctx.send("I'm not in a voice channel.")

async def make_call(to_number, from_number):
    twiml = f"""
    <Response>
        <Connect>
            <Stream url="{config.WEBSOCKET_URL}">
                <Parameter name="from" value="{from_number}"/>
                <Parameter name="to" value="{to_number}"/>
            </Stream>
        </Connect>
    </Response>
    """
    call = twilio_client.calls.create(
        to=to_number,
        from_=from_number,
        twiml=twiml
    )
    return call.sid

async def start_call(to_number, voice_client, channel_id, user_id):
    global current_calls
    if current_calls >= config.MAX_CONCURRENT_CALLS:
        await tts.play_tts(voice_client, "Maximum concurrent calls reached. Please try again later.")
        return None
    from_number = random.choice(config.TWILIO_NUMBERS)
    try:
        call_sid = await make_call(to_number, from_number)
    except Exception as e:
        await tts.play_tts(voice_client, f"Failed to initiate call: {str(e)}")
        return None

    bridge = AudioBridge(call_sid, voice_client)
    active_bridges[call_sid] = bridge
    current_calls += 1

    discord_handler = DiscordAudioHandler(voice_client)
    await discord_handler.start_listening(None, None, bridge)
    await bridge.start()

    await database.log_call_start(call_sid, channel_id, user_id, to_number, from_number)
    await tts.play_tts(voice_client, f"Calling {to_number}...")

    return call_sid

async def handle_voice_command(voice_client, channel_id, user_id, transcript):
    transcript = transcript.lower().strip()
    if transcript.startswith("call "):
        number = transcript[5:].replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if number.isdigit() and len(number) >= 10:
            await start_call(number, voice_client, channel_id, user_id)
        else:
            await tts.play_tts(voice_client, "Invalid phone number. Please say a valid number.")
    else:
        pass

async def media_stream_handler(websocket, path):
    call_sid = None
    bridge = None
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["event"] == "start":
                call_sid = data["stream"]["callSid"]
                bridge = active_bridges.get(call_sid)
                if not bridge:
                    print(f"Received stream for unknown call {call_sid}")
                    await websocket.close()
                    return
            elif data["event"] == "media":
                if bridge:
                    ulaw = base64.b64decode(data["media"]["payload"])
                    pcm = ulaw_to_pcm(ulaw)
                    await bridge.twilio_audio_received(pcm)
            elif data["event"] == "stop":
                if call_sid:
                    await database.log_call_end(call_sid)
                    if bridge:
                        await bridge.stop()
                    if call_sid in active_bridges:
                        del active_bridges[call_sid]
                        global current_calls
                        current_calls -= 1
                    if bridge and bridge.voice_client:
                        await tts.play_tts(bridge.voice_client, "Call ended.")
                break
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if call_sid and call_sid in active_bridges:
            del active_bridges[call_sid]
            current_calls -= 1

def ulaw_to_pcm(ulaw_bytes):
    from pydub import AudioSegment
    audio = AudioSegment(data=ulaw_bytes, sample_width=1, frame_rate=8000, channels=1)
    audio = audio.set_sample_width(2)
    audio = audio.set_frame_rate(48000)
    return audio.raw_data

def pcm_to_ulaw(pcm_bytes):
    import audioop
    downsampled = audioop.ratecv(pcm_bytes, 2, 1, 48000, 8000, None)[0]
    ulaw = audioop.lin2ulaw(downsampled, 2)
    return ulaw

async def wake_and_recognize(voice_client, channel_id, user_id):
    wake = WakeWordDetector()
    recognizer = SpeechRecognizer()
    handler = DiscordAudioHandler(voice_client)
    await handler.start_listening(wake, recognizer)
    transcript = await recognizer.get_command()
    if transcript:
        await handle_voice_command(voice_client, channel_id, user_id, transcript)
    await recognizer.stop()

async def start_command_listening(voice_client, channel_id, user_id):
    asyncio.create_task(wake_and_recognize(voice_client, channel_id, user_id))

async def main():
    global ws_server
    ws_server = await websockets.serve(media_stream_handler, "0.0.0.0", config.WEBSOCKET_PORT)
    print(f"WebSocket server started on port {config.WEBSOCKET_PORT}")
    await bot.start(config.DISCORD_TOKEN)
    await asyncio.gather(ws_server.wait_closed(), bot.wait_until_ready())

if __name__ == "__main__":
    asyncio.run(main())
