import discord
from discord import app_commands
import asyncio
import requests
import json
from datetime import datetime, timedelta, timezone
import os
import re
from discord.app_commands import check, CheckFailure

CONFIG_FILE = "guild_config.json"
MAX_COUNT_FILE = "max_player_count.json"
STATUS_FILE = "server_status.json"
URL = "https://dunestatus.com"
COOLDOWN_MINUTES = 5

# Use fixed offset for CEST (UTC+2) without DST changes
CEST = timezone(timedelta(hours=2))

intents = discord.Intents.default()
intents.members = True  # Needed for permission checks
intents.guilds = True   # Needed to fetch guild and channels properly
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

guild_configs = {}
max_counts = {}
status_info = {}
                                                                                                                                                                                         last_statuses = {}                                                                                                                                                                       last_status_changes = {}                                                                                                                                                                                                                                                                                                                                                          last_reset_day = None                                                                                                                                                                    ratelimit_calls = {}

_server_data_cache = None
_server_data_cache_time = None
_server_list_cache = []
_server_list_cache_time = None

last_fetch_time = None

# Supported languages and translations
LANGUAGES = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Fran      ais",
    "es": "Espa      ol"
}

# Translation dictionary for all bot messages and embed fields
TRANSLATIONS = {
    "Serverstatus": {
        "en": "Serverstatus",
        "de": "Serverstatus",
        "fr": "Statut du serveur",
        "de": "Serverstatus",
        "fr": "Statut du serveur",
        "es": "Estado del servidor"
    },
    "Status": {
        "en": "Status",
        "de": "Status",
        "fr": "Statut",
        "es": "Estado"
    },
    "Server": {
        "en": "Server",
        "de": "Server",
        "fr": "Serveur",
        "es": "Servidor"
    },
    "Sietch": {
        "en": "Sietch",
        "de": "Sietch",
        "fr": "Sietch",
        "es": "Sietch"
    },
    "Playercount Sietch": {
        "en": "Playercount Sietch",
        "de": "Spielerzahl Sietch",
        "fr": "Joueurs Sietch",
        "es": "Jugadores Sietch"
    },
    "Daily Player Peak Sietch": {                                                                                                                                                                "en": "Daily Player Peak Sietch",                                                                                                                                                        "de": "T      glicher Spielerrekord Sietch",                                                                                                                                             "fr": "Pic journalier joueurs Sietch",                                                                                                                                                   "es": "Pico diario jugadores Sietch"                                                                                                                                                 },
    "Capacity Sietch": {
        "en": "Capacity Sietch",
        "de": "Kapazit      t Sietch",
        "fr": "Capacit       Sietch",
        "es": "Capacidad Sietch"
    },
    "Playercount Server": {
        "en": "Playercount Server",
        "de": "Spielerzahl Server",
        "fr": "Joueurs Serveur",
        "es": "Jugadores Servidor"
    },
    "Daily Player Peak Server": {
        "en": "Daily Player Peak Server",
        "de": "Taeglicher Spielerrekord Server",
        "fr": "Pic journalier joueurs Serveur",
        "es": "Pico diario jugadores Servidor"
    },
    "Capacity Server": {
        "en": "Capacity Server",
        "de": "Kapazitaet Server",
        "fr": "Capacite Serveur",
        "es": "Capacidad Servidor"
    },
    "Last status update:": {
        "en": "Last status update:",
        "de": "Letztes Status-Update:",
        "fr": "Derni      re mise        jour :",
        "es": "   ^zltima actualizaci      n:"
    },
    "Please don't request so often (max 5 per minute).": {
        "en": "Please don't request so often (max 5 per minute).",
        "de": "Bitte nicht so oft anfragen (max. 5 pro Minute).",
        "fr": "Merci de ne pas demander aussi souvent (max 5 par minute).",
        "es": "Por favor, no solicites tan seguido (m      x. 5 por minuto)."
    },
    "Please configure first using /daconfig or specify server and sietch.": {
        "en": "Please configure first using /daconfig or specify server and sietch.",
        "de": "Bitte zuerst mit /daconfig konfigurieren oder Server und Sietch angeben.",
        "fr": "Veuillez d'abord configurer avec /daconfig ou sp      cifier serveur et sietch.",
        "es": "Por favor configura primero con /daconfig o especifica servidor y sietch."
    },
    "Could not retrieve data for server '{server_name}'.": {
        "en": "Could not retrieve data for server '{server_name}'.",
        "de": "Daten f      r Server '{server_name}' konnten nicht abgerufen werden.",
        "fr": "Impossible de r      cup      rer les donn      es pour le serveur '{server_name}'.",
        "es": "No se pudieron obtener datos para el servidor '{server_name}'."
    },
    "Configuration saved:\nServer: {server_name}\nSietch: {sietch_name}\nChannel: {channel}\nOnline/Offline messages: {online_offline}\nDaily Player Peak posting: {max24h_post}\nStatus visibility: {visibility}": {
        "en": "Configuration saved:\nServer: {server_name}\nSietch: {sietch_name}\nChannel: {channel}\nOnline/Offline messages: {online_offline}\nDaily Player Peak posting: {max24h_post}\nStatus visibility: {visibility}",
        "de": "Konfiguration gespeichert:\nServer: {server_name}\nSietch: {sietch_name}\nKanal: {channel}\nOnline/Offline Nachrichten: {online_offline}\nTaegliche Spielerrekord Meldung: {max24h_post}\nStatus Sichtbarkeit: {visibility}",
        "fr": "Configuration enregistre :\nServeur : {server_name}\nSietch : {sietch_name}\nCanal : {channel}\nMessages en ligne/hors ligne : {online_offline}\nPublication du pic journalier : {max24h_post}\nVisibilite du statut : {visibility}",
        "es": "Configuracin guardada:\nServidor: {server_name}\nSietch: {sietch_name}\nCanal: {channel}\nMensajes online/offline: {online_offline}\nPublicacin pico diario: {max24h_post}\nVisibilidad del estado: {visibility}"
    },    
    "You need administrator rights to use this command.": {
        "en": "You need administrator rights to use this command.",
        "de": "Du benoetigst Administratorrechte, um diesen Befehl zu verwenden.",
        "fr": "Vous devezetre administrateur pour utiliser cette commande.",
        "es": "Necesitas derechos de administrador para usar este comando."
    },
    "Sietch offline": {
        "en": "**Sietch offline**",
        "de": "**Sietch offline**",
        "fr": "**Sietch hors ligne**",
        "es": "**Sietch desconectado**"
    },
    "Sietch online": {
        "en": "**Sietch online**",
        "de": "**Sietch online**",
        "fr": "**Sietch en ligne**",
        "es": "**Sietch conectado**"
    },
    "Daily Player Peak": {
        "en": "**Daily Player Peak**",
        "de": "**Taeglicher Spielerrekord**",
        "fr": "**Pic journalier joueurs**",
        "es": "**Pico diario jugadores**"
    },
    "Player": {
        "en": "Player",
        "de": "Spieler",
        "fr": "Joueur",
        "es": "Jugador"
    },
    "I'll update you about the status of {server_name} - {sietch_name} in this channel.": {
        "en": "I'll update you about the status of {server_name} - {sietch_name} in this channel.",
        "de": "Ich werde dich in diesem Kanal       ber den Status von {server_name} - {sietch_name} informieren.",
        "fr": "Je vous tiendrai inform       du statut de {server_name} - {sietch_name} dans ce canal.",
        "es": "Te mantendr       informado sobre el estado de {server_name} - {sietch_name} en este canal."
    }
}

def translate(key: str, lang: str = "en", **kwargs) -> str:
    text = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("en", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text

def load_guild_configs():
    global guild_configs
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    guild_configs = json.loads(content)
                else:
                    guild_configs = {}
        except Exception as e:
            print(f"{datetime.utcnow()} - Error loading guild config: {e}")
            guild_configs = {}
    else:
        guild_configs = {}

def save_guild_configs():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(guild_configs, f, indent=2)
    except Exception as e:
        print(f"{datetime.utcnow()} - Error saving guild config: {e}")

def load_max_counts():
    global max_counts
    if os.path.isfile(MAX_COUNT_FILE):
        try:
            with open(MAX_COUNT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    loaded = json.loads(content)
                    max_counts.clear()
                    for k, v in loaded.items():
                        parts = k.split("|", 1)
                        if len(parts) == 2:
                            max_counts[(parts[0], parts[1])] = v
                else:
                    max_counts.clear()
        except Exception as e:
            print(f"{datetime.utcnow()} - Error loading max counts: {e}")
            max_counts.clear()
    else:
        max_counts.clear()

def save_max_counts():
    try:
        to_save = {f"{k[0]}|{k[1]}": v for k, v in max_counts.items()}
        with open(MAX_COUNT_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"{datetime.utcnow()} - Error saving max counts: {e}")

def load_status_info():
    global status_info
    if os.path.isfile(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    loaded = json.loads(content)
                    status_info.clear()
                    for k, v in loaded.items():
                        parts = k.split("|", 1)
                        if len(parts) == 2:
                            last_change = None
                            if v.get("last_change"):
                                try:
                                    last_change = datetime.fromisoformat(v["last_change"])
                                except Exception:
                                    last_change = None
                            status_info[(parts[0], parts[1])] = {
                                "status": v.get("status"),
                                "last_change": last_change
                            }
                else:
                    status_info.clear()
        except Exception as e:
            print(f"{datetime.utcnow()} - Error loading status info: {e}")
            status_info.clear()
    else:
        status_info.clear()

def save_status_info():
    try:
        to_save = {}
        for k, v in status_info.items():
            to_save[f"{k[0]}|{k[1]}"] = {
                "status": v.get("status"),
                "last_change": v.get("last_change").isoformat() if v.get("last_change") else None
            }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
    except Exception as e:
        print(f"{datetime.utcnow()} - Error saving status info: {e}")

def find_balanced_braces_around(text, start_pos):
    open_pos = text.rfind('{', 0, start_pos)
    if open_pos == -1:
        return None
    brace_count = 0
    for i in range(open_pos, len(text)):
        if text[i] == '{': brace_count += 1
        elif text[i] == '}': brace_count -= 1
        if brace_count == 0:
            return text[open_pos:i+1]
    return None

def _fetch_raw_data():
    global last_fetch_time
    try:
        r = requests.get(URL, timeout=5)
        r.raise_for_status()
        last_fetch_time = datetime.utcnow()
        return r.text
    except Exception as e:
        print(f"{datetime.utcnow()} - Error fetching raw data: {e}")
        return None

def _update_server_data_cache():
    global _server_data_cache, _server_data_cache_time, _server_list_cache, _server_list_cache_time
    now = datetime.utcnow()
    if _server_data_cache_time and (now - _server_data_cache_time).total_seconds() < 60:
        return  # Cache still valid

    raw = _fetch_raw_data()
    if not raw:
        return

    servers = {}
    sietches_set = set()
    pattern = r'\\"DisplayName\\":\\"(.*?)\\"'
    matches = list(re.finditer(pattern, raw))
    for m in matches:
        server_name = m.group(1)
        pos = m.start()
        block = find_balanced_braces_around(raw, pos)
        if not block:
            continue
        try:
            data = json.loads(block.encode('utf-8').decode('unicode_escape'))
            if data.get("DisplayName") == server_name:
                servers[server_name] = data
                for sietch in data.get("ActiveInitialServers", []):
                    sname = sietch.get("DisplayName", "").strip()
                    if sname:
                        sietches_set.add(sname)
        except:
            continue

    filtered_servers = {k: v for k, v in servers.items() if k not in sietches_set}

    _server_data_cache = filtered_servers
    _server_data_cache_time = now

    _server_list_cache = list(filtered_servers.keys())
    _server_list_cache_time = now

def fetch_server_block(server_name):
    _update_server_data_cache()
    if _server_data_cache is None:
        return None
    return _server_data_cache.get(server_name)

async def fetch_all_servers():
    now = datetime.utcnow()
    global _server_list_cache, _server_list_cache_time
    if _server_list_cache_time and (now - _server_list_cache_time).total_seconds() < 60 and _server_list_cache:
        return _server_list_cache
    _update_server_data_cache()
    return _server_list_cache

async def autocomplete_server_name(interaction: discord.Interaction, current: str):
    servers = await fetch_all_servers()
    return [
        app_commands.Choice(name=s, value=s)
        for s in servers if current.lower() in s.lower()
    ][:25]

async def autocomplete_sietch_name(interaction: discord.Interaction, current: str):
    server_name = None
    for option in getattr(interaction, "options", []):
        if option.name == "server_name":
            server_name = option.value
            break
    if not server_name:
        for opt in interaction.data.get("options", []):
            if opt["name"] == "server_name":
                server_name = opt.get("value")
                break
    if not server_name:
        return []

    server_data = fetch_server_block(server_name)
    if not server_data:
        return []

    sietches = [s.get("DisplayName", "") for s in server_data.get("ActiveInitialServers", [])]
    return [
        app_commands.Choice(name=s, value=s)
        for s in sietches if current.lower() in s.lower()
    ][:25]

def create_status_embed(server_data, sietch_name, max_count_server, max_count_sietch, lang):
    sietch = next((s for s in server_data.get("ActiveInitialServers", []) if s.get("DisplayName", "").strip() == sietch_name), None)
    if sietch:
        status_sietch = translate("Online", lang) if sietch.get("ServerStatus", 0) == 20 else translate("Offline", lang)
        playercount_sietch = sietch.get("CurrentConcurrentPlayerCount", 0)
        capacity_sietch = sietch.get("MaxConcurrentPlayerCapacity", 0)
    else:
        status_sietch = translate("Unknown", lang)
        playercount_sietch = 0
        capacity_sietch = 0

    status_server = translate("Online", lang) if server_data.get("ServerStatus", 0) == 20 else translate("Offline", lang)

    sietch_short = sietch_name[len("Sietch "):] if sietch_name and sietch_name.startswith("Sietch ") else sietch_name or translate("Sietch", lang)

    embed = discord.Embed(title=translate("Serverstatus", lang), color=0x1F8B4C, timestamp=datetime.utcnow())

    embed.add_field(name=translate("Status", lang), value=status_sietch, inline=True)
    embed.add_field(name=translate("Server", lang), value=server_data.get("DisplayName", "unknown"), inline=True)
    embed.add_field(name=translate("Sietch", lang), value=sietch_short, inline=True)

    embed.add_field(name=translate("Playercount Sietch", lang), value=str(playercount_sietch), inline=True)
    embed.add_field(name=translate("Daily Player Peak Sietch", lang), value=str(max_count_sietch), inline=True)
    embed.add_field(name=translate("Capacity Sietch", lang), value=str(capacity_sietch), inline=True)

    embed.add_field(name=translate("Playercount Server", lang), value=str(server_data.get("BattlegroupCurrentActive", 0)), inline=True)
    embed.add_field(name=translate("Daily Player Peak Server", lang), value=str(max_count_server), inline=True)
    embed.add_field(name=translate("Capacity Server", lang), value=str(server_data.get("BattlegroupMaxPlayerCapacity", 0)), inline=True)

    if last_fetch_time:
        embed.set_footer(text=f"{translate('Last status update:', lang)} {last_fetch_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    else:
        embed.set_footer(text=f"{translate('Last status update:', lang)} unknown")

    return embed

def create_update_embed(title, desc, color):
    embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.utcnow())
    embed.set_footer(text="Dune Awakening Status Bot")
    return embed

def is_guild_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        member = interaction.user
        if not isinstance(member, discord.Member):
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except:
                return False
        return member.guild_permissions.administrator
    return check(predicate)

LANGUAGE_CHOICES = [
    app_commands.Choice(name="English", value="en"),
    app_commands.Choice(name="Deutsch", value="de"),
    app_commands.Choice(name="Fran      ais", value="fr"),
    app_commands.Choice(name="Espa      ol", value="es"),
]

STATUS_VISIBILITY_CHOICES = [
    app_commands.Choice(name="Private (ephemeral)", value="private"),
    app_commands.Choice(name="Public (channel)", value="public"),
]

@tree.command(name="daconfig", description="Configure Dune Awakening server and sietch")
@is_guild_admin()
@app_commands.describe(
    server_name="Main server name (e.g. Rhea)",
    sietch_name="Sietch/subserver name",
    channel="Channel for status messages",
    online_offline="Send online/offline messages",
    max24h_post="Post daily player peak",
    language="Language for bot messages",
    status_visibility="Visibility of /dastatus replies"
)
@app_commands.autocomplete(server_name=autocomplete_server_name)
@app_commands.autocomplete(sietch_name=autocomplete_sietch_name)
@app_commands.choices(language=LANGUAGE_CHOICES, status_visibility=STATUS_VISIBILITY_CHOICES)
async def daconfig(
    interaction: discord.Interaction,
    server_name: str = None,
    sietch_name: str = None,
    channel: discord.TextChannel = None,
    online_offline: bool = None,
    max24h_post: bool = None,
    language: str = None,
    status_visibility: str = None,
):
    guild_id = str(interaction.guild_id)
    config = guild_configs.get(guild_id, {})

    # If server_name is changed, sietch_name must be provided
    if server_name is not None:
        if sietch_name is None:
            await interaction.response.send_message(
                translate("If you change the server, you must also specify the sietch.", config.get("language", "en")),
                ephemeral=True,
            )
            return
    else:
        # Use existing config values if parameters not provided
        server_name = config.get("server_name")
        if sietch_name is None:
            sietch_name = config.get("sietch_name")

    channel_id = config.get("channel_id")
    if channel is not None:
        channel_id = channel.id

    online_offline_val = config.get("online_offline")
    if online_offline is not None:
        online_offline_val = online_offline

    max24h_post_val = config.get("max24h_post")
    if max24h_post is not None:
        max24h_post_val = max24h_post

    language_val = config.get("language", "en")
    if language in [choice.value for choice in LANGUAGE_CHOICES]:
        language_val = language

    status_visibility_val = config.get("status_visibility", "private")
    if status_visibility in [choice.value for choice in STATUS_VISIBILITY_CHOICES]:
        status_visibility_val = status_visibility

    guild_configs[guild_id] = {
        "server_name": server_name,
        "sietch_name": sietch_name,
        "channel_id": channel_id,
        "online_offline": online_offline_val,
        "max24h_post": max24h_post_val,
        "language": language_val,
        "status_visibility": status_visibility_val,
    }
    save_guild_configs()

    try:
        guild = interaction.guild or await interaction.client.fetch_guild(interaction.guild_id)
        target_channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
        if target_channel:
            await target_channel.send(
                translate(
                    "I'll update you about the status of {server_name} - {sietch_name} in this channel.",
                    language_val,
                    server_name=server_name,
                    sietch_name=sietch_name,
                )
            )
    except Exception as e:
        print(f"{datetime.utcnow()} - Failed to send update message in channel: {e}")

    await interaction.response.send_message(
        translate(
            "Configuration saved:\nServer: {server_name}\nSietch: {sietch_name}\nChannel: {channel}\nOnline/Offline messages: {online_offline}\nDaily Player Peak posting: {max24h_post}\nStatus visibility: {visibility}",
            language_val,
            server_name=server_name,
            sietch_name=sietch_name,
            channel=f"<#{channel_id}>" if channel_id else "None",
            online_offline="Yes" if online_offline_val else "No",
            max24h_post="Yes" if max24h_post_val else "No",
            visibility=("Private (ephemeral)" if status_visibility_val == "private" else "Public (channel)"),
        ),
        ephemeral=True,
    )

@daconfig.error
async def daconfig_error(interaction: discord.Interaction, error):
    from discord.app_commands import CheckFailure
    if isinstance(error, CheckFailure):
        lang = "en"
        config = guild_configs.get(str(interaction.guild_id))
        if config:
            lang = config.get("language", "en")
        await interaction.response.send_message(translate("You need administrator rights to use this command.", lang), ephemeral=True)

@tree.command(name="dastatus", description="Get current server status or specify server and sietch")
@app_commands.describe(
    server_name="Main server name (optional)",
    sietch_name="Sietch/subserver name (optional)"
)
@app_commands.autocomplete(server_name=autocomplete_server_name)
@app_commands.autocomplete(sietch_name=autocomplete_sietch_name)
async def dastatus(interaction: discord.Interaction, server_name: str = None, sietch_name: str = None):
    guild_id = str(interaction.guild_id)
    now = datetime.utcnow()
    timestamps = ratelimit_calls.setdefault(guild_id, [])
    timestamps = [t for t in timestamps if (now - t).total_seconds() < 60]
    if len(timestamps) >= 5:
        lang = "en"
        config = guild_configs.get(guild_id)
        if config:
            lang = config.get("language", "en")
        await interaction.response.send_message(translate("Please don't request so often (max 5 per minute).", lang), ephemeral=True)
        return
    timestamps.append(now)
    ratelimit_calls[guild_id] = timestamps

    config = guild_configs.get(guild_id, {})
    lang = config.get("language", "en")
    visibility = config.get("status_visibility", "private")

    if server_name is None or sietch_name is None:
        if not config:
            await interaction.response.send_message(translate("Please configure first using /daconfig or specify server and sietch.", lang), ephemeral=True)
            return
        if server_name is None:
            server_name = config.get("server_name")
        if sietch_name is None:
            sietch_name = config.get("sietch_name")

    server_data = fetch_server_block(server_name)
    if not server_data:
        await interaction.response.send_message(translate("Could not retrieve data for server '{server_name}'.", lang, server_name=server_name), ephemeral=True)
        return

    max_server = max_counts.get((server_name, ""), 0)
    max_sietch = max_counts.get((server_name, sietch_name), 0)

    embed = create_status_embed(server_data, sietch_name, max_server, max_sietch, lang)

    await interaction.response.send_message(embed=embed, ephemeral=(visibility == "private"))

async def periodic_check():
    global last_reset_day
    load_guild_configs()
    load_max_counts()
    load_status_info()
    last_reset_day = datetime.now(CEST).date()

    while True:
        now_utc = datetime.utcnow()
        now_cest = datetime.now(CEST)
        today_cest = now_cest.date()

        _update_server_data_cache()

        all_servers = _server_data_cache or {}

        changed_max = False
        changed_status = False

        for server_name, server_data in all_servers.items():
            current_count_server = server_data.get("BattlegroupCurrentActive", 0)
            key_server = (server_name, "")
            old_max_server = max_counts.get(key_server, 0)
            if current_count_server > old_max_server:
                max_counts[key_server] = current_count_server
                changed_max = True

            current_status_server = server_data.get("ServerStatus")
            old_status_server = status_info.get(key_server, {}).get("status")
            if old_status_server != current_status_server:
                status_info[key_server] = {
                    "status": current_status_server,
                    "last_change": now_utc
                }
                changed_status = True

            for sietch in server_data.get("ActiveInitialServers", []):
                sietch_name = sietch.get("DisplayName", "").strip()
                current_count_sietch = sietch.get("CurrentConcurrentPlayerCount", 0)
                key_sietch = (server_name, sietch_name)
                old_max_sietch = max_counts.get(key_sietch, 0)
                if current_count_sietch > old_max_sietch:
                    max_counts[key_sietch] = current_count_sietch
                    changed_max = True

                current_status_sietch = sietch.get("ServerStatus")
                old_status_sietch = status_info.get(key_sietch, {}).get("status")
                if old_status_sietch != current_status_sietch:
                    status_info[key_sietch] = {
                        "status": current_status_sietch,
                        "last_change": now_utc
                    }
                    changed_status = True

        if changed_max:
            save_max_counts()
        if changed_status:
            save_status_info()

        for guild_id, config in guild_configs.items():
            guild = client.get_guild(int(guild_id))
            if guild is None:
                try:
                    guild = await client.fetch_guild(int(guild_id))
                except Exception as e:
                    print(f"{datetime.utcnow()} - Failed to fetch guild {guild_id}: {e}")
                    continue

            channel = guild.get_channel(config.get("channel_id"))
            if not channel:
                try:
                    channel = await guild.fetch_channel(config.get("channel_id"))
                except Exception:
                    channel = None
                if not channel:
                    print(f"{datetime.utcnow()} - Channel {config.get('channel_id')} for guild {guild_id} not found.")
                    continue

            server_name = config["server_name"]
            sietch_name = config["sietch_name"]
            lang = config.get("language", "en")

            key_sietch = (server_name, sietch_name)

            current_status_sietch = status_info.get(key_sietch, {}).get("status")

            if guild_id not in last_statuses:
                last_statuses[guild_id] = {"sietch": None}
            if guild_id not in last_status_changes:
                last_status_changes[guild_id] = now_utc - timedelta(minutes=COOLDOWN_MINUTES+1)

            last_stat_sietch = last_statuses[guild_id].get("sietch")
            last_change = last_status_changes[guild_id]
            cooldown_passed = (now_utc - last_change) > timedelta(minutes=COOLDOWN_MINUTES)

            if config.get("online_offline", False):
                if last_stat_sietch == 20 and current_status_sietch != 20 and cooldown_passed:
                    msg = f"Server {server_name} - {sietch_name} went offline."
                    await channel.send(embed=create_update_embed(translate("Sietch offline", lang), msg, 0xFF0000))
                    last_status_changes[guild_id] = now_utc
                elif last_stat_sietch != 20 and current_status_sietch == 20 and cooldown_passed:
                    msg = f"Server {server_name} - {sietch_name} is online again."
                    await channel.send(embed=create_update_embed(translate("Sietch online", lang), msg, 0x00FF00))
                    last_status_changes[guild_id] = now_utc

            last_statuses[guild_id]["sietch"] = current_status_sietch

        if now_cest.hour == 10 and now_cest.minute == 0 and last_reset_day != today_cest:
            for guild_id, config in guild_configs.items():
                guild = client.get_guild(int(guild_id))
                if guild is None:
                    try:
                        guild = await client.fetch_guild(int(guild_id))
                    except Exception:
                        continue
                if not config.get("max24h_post", False):
                    continue
                channel = guild.get_channel(config.get("channel_id"))
                if not channel:
                    try:
                        channel = await guild.fetch_channel(config.get("channel_id"))
                    except Exception:
                        channel = None
                    if not channel:
                        continue

                server_name = config.get("server_name")
                sietch_name = config.get("sietch_name")
                lang = config.get("language", "en")
                sietch_short = sietch_name[len("Sietch "):] if sietch_name and sietch_name.startswith("Sietch ") else sietch_name or "Sietch"

                max_server = max_counts.get((server_name, ""), 0)
                max_sietch = max_counts.get((server_name, sietch_name), 0)

                text = f"{translate('Daily Player Peak', lang)}\n{server_name}: {max_server} {translate('Player', lang)}\n{sietch_short}: {max_sietch} {translate('Player', lang)}"
                await channel.send(embed=create_update_embed(text, "", 0xFFFF00))

            max_counts.clear()
            save_max_counts()
            last_reset_day = today_cest

        await asyncio.sleep(60)

@client.event
async def on_ready():
    await tree.sync()
    print(f"{datetime.utcnow()} - Bot started as {client.user}")

async def main():
    load_guild_configs()
    load_max_counts()
    load_status_info()
    async with client:
        client.loop.create_task(periodic_check())
        await client.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
