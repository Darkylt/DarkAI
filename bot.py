from better_profanity import profanity as pf
from config import BotConfig
from config import LLMConfig
from config import SDConfig
from config import validate_config
from datetime import datetime
from llama_cpp import Llama
from PIL import Image, PngImagePlugin

import asyncio
import base64
import copy
import hikari
import io
import lightbulb
import requests

validate_config()

# Logging in the Bot
bot = lightbulb.BotApp(
    token=BotConfig.token,
    default_enabled_guilds=(BotConfig.guild)
)

# Create an instance of the LLM
llm = Llama(model_path=LLMConfig.model_path, 
            n_ctx=512,
            seed=LLMConfig.model_seed,
            n_parts=-1,
            f16_kv=True,
            logits_all=False,
            vocab_only=False,
            use_mmap=True,
            use_mlock=False,
            embedding=False,
            n_threads=LLMConfig.num_threads,
            n_batch=512,
            last_n_tokens_size=64,
            verbose=True,
            )

def log_message(user_name, user_prompt, response, dm: bool):
    """
    Logs the chat message to a file.

    Args:
        user_name (str): The username of the sender.
        user_prompt (str): The user's message.
        response (str): The AI's response.
        dm (bool): Specifies if the message should be saved to the DM chatlog or the regular Chatlog
    """

    oneline_user_prompt = user_prompt.replace('\n', ' ')
    oneline_response = response.replace('\n', ' ')

    if dm:
        with open("chathistory+\complete_dm_chathistory.txt", "a", encoding="utf-8") as complete_dm_file:
            complete_dm_file.write(f"{user_name}: {oneline_user_prompt}\n{LLMConfig.ai_name}: {oneline_response}\n")
    
        with open("chathistory+\complete_dm_chathistory.txt", "r", encoding="utf-8") as complete_dm_file:
            lines = complete_dm_file.readlines()
            last_lines = lines[-LLMConfig.chat_memory_length:]

        with open("chathistory+\dm_chathistory.txt", "w", encoding="utf-8") as dm_file:
            for line in last_lines:
                truncated_line = line[:500]  # Limit line length to 500 characters
                dm_file.write(truncated_line)

    else:
        # Writes to the History with the Appropiate amount of lines and to the complete chathistory file
        with open("chathistory+/complete_chathistory.txt", "a", encoding="utf-8") as complete_chathistory:
            complete_chathistory.write(f"{user_name}: {oneline_user_prompt}\n{LLMConfig.ai_name}: {oneline_response}\n")
        
        with open("chathistory+/complete_chathistory.txt", "r", encoding="utf-8") as complete_file:
            lines = complete_file.readlines()
            if len(lines) <= LLMConfig.chat_memory_length:
                with open("chathistory+/chathistory.txt", "w", encoding="utf-8") as history_file:
                    history_file.write("".join(lines))
            else:
                with open("chathistory+/chathistory.txt", "w", encoding="utf-8") as history_file:
                    history_file.write("".join(lines[-LLMConfig.chat_memory_length:]))

#Startup logic
#Does nothing important at the moment
@bot.listen(hikari.StartedEvent)
async def on_startup(event: hikari.StartedEvent):
    print("Bot is online!")

#/help Command
@bot.command
@lightbulb.command("help", "Hilfe mit dem Bot")
@lightbulb.implements(lightbulb.SlashCommand)
async def help_command(ctx: lightbulb.SlashContext) -> None:
    """
    The /help command.
    Responds with the Help Message Defined in the config.yml
    Adds an Indicator if the bot is in dev mode.
    """
    if BotConfig.dev_mode:
        await ctx.respond(f"{BotConfig.help_message}\n(I am in Dev Mode. I may not work as intended.)")
    else:
        await ctx.respond(BotConfig.help_message)

@bot.listen(hikari.GuildMessageCreateEvent)
async def chat(event: hikari.GuildMessageCreateEvent) -> None:
    """
    The Chatbot function of the Bot.
    """
    response = ""

    if not event.is_human:
        return
    
    me = bot.get_me()

    if me.id in event.message.user_mentions_ids:
        user_prompt = event.message.content.replace("<@820739005103472691> ", "").replace("<@820739005103472691>", "") #Getting the question and removing the mention
        filtered_user_prompt = pf.censor(event.message.content.replace("<@820739005103472691> ", "").replace("<@820739005103472691>", ""))

        user_name = event.author.username

        if BotConfig.dev_mode:
            response_message = await event.message.respond("Generating answer...\n(I am in Dev Mode. Some functions may not work.)")
        else:
            response_message = await event.message.respond("Generating answer...")

        if filtered_user_prompt != user_prompt:
            if BotConfig.dev_mode:
                await event.app.rest.edit_message(response_message.channel_id, response_message.id, content="Your message contains a 'bad word'. I can not respond to this.\n(I am in Dev Mode. Report this Message to Darkyl if this is an Error)")
            else:
                await event.app.rest.edit_message(response_message.channel_id, response_message.id, content="Your message contains a 'bad word'. I can not respond to this. If you believe this is an error please message Darkyl.")
            return

        #Defining the task for the AI
        stream = llm(
            f"{LLMConfig.prompt}\n\n{LLMConfig.chat_history}{user_name}: {user_prompt}\n{LLMConfig.ai_name}: ",
            max_tokens=100,
            temperature=0.8,
            stop=["\n", f"{user_name}:"],
            stream=True,
        )
        
        for output in stream:
            completionFragment = copy.deepcopy(output)
            response += completionFragment["choices"][0]["text"]

            filtered_response = pf.censor(response)

            if response == "":
                if BotConfig.dev_mode:
                    rsp = await event.app.rest.edit_message(response_message.channel_id, response_message.id, content="There was an error while generating the message....\n(I am in Dev Mode. Some functions may not work)")
                else:
                    rsp = await event.app.rest.edit_message(response_message.channel_id, response_message.id, content="There was an error while generating the message....")
            else:
                if BotConfig.dev_mode:
                    rsp = await event.app.rest.edit_message(response_message.channel_id, response_message.id, content=f"{filtered_response}\n(I am in Dev Mode. Some functions may not work)")
                else:
                    rsp = await event.app.rest.edit_message(response_message.channel_id, response_message.id, content=f"{filtered_response}")
        
        print("Generation Finished")

        log_message(user_name=user_name, user_prompt=user_prompt, response=filtered_response, dm=False)

        await rsp.add_reaction("✅")
        

#Memory Wipe command
@bot.command
@lightbulb.add_checks(lightbulb.has_roles(962078064869797958)) #Only Admin role can execute this command
@lightbulb.command("wipe", "Allows Darkyl to reset the Chat Memory")
@lightbulb.implements(lightbulb.SlashCommand)
async def memory_wipe(ctx: lightbulb.SlashContext) -> None:

    #Overwriting the chat history with the default start histroy
    with open("chathistory+/chathistory.txt", "w", encoding="utf-8") as history_file:
        history_file.write(LLMConfig.default_chat_history)
    with open("chathistory+/complete_chathistory.txt", "w", encoding="utf-8") as complete_file:
        complete_file.write(LLMConfig.default_chat_history)
    
    #Sending feedback in Discord
    await ctx.respond("Memory wiped. I can not remember any previous messages including this one.")
    
    #print("Chat Memory Wiped.")

#Logic for generating the image
async def generate_image(user_name: str, user_discriminator: str, prompt: str, private: bool, steps: int, width: int, height: int, negative_prompt) -> str:
    payload = {"prompt": prompt, "negative_prompt": negative_prompt,"steps": steps, "width": width, "height": height}

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    try:
        #Sending Image generation request to the API
        response = requests.post(url=f"{BotConfig.url}/sdapi/v1/txt2img", json=payload)
        r = response.json()

        #Waiting for the Image to finish and then saving it.
        for i in r["images"]:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
            png_payload = {"image": "data:image/png;base64," + i}
            response2 = requests.post(url=f"{BotConfig.url}/sdapi/v1/png-info", json=png_payload)
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("parameters", response2.json().get("info"))
            if private:
                image_path = f"image_folder/{timestamp}__{user_name}#{user_discriminator}_with the prompt_{prompt}_[PRIVATE GENERATION].png"
            else:
                image_path = f"image_folder/{timestamp}__{user_name}#{user_discriminator}_with the prompt_{prompt}.png"
            image.save(image_path, pnginfo=pnginfo)
            image.save('output.png')

        return image_path

    except Exception as e:
        print(f"Folgender Fehler ist beim generieren des Bildes aufgetreten: {str(e)}")
        return None

#Sends the image
async def send_image(ctx: lightbulb.SlashContext) -> None:
    """
    Sends the generated image as a file attachment in the specified context.
    """
    try:
        channel = await ctx.bot.rest.fetch_channel(SDConfig.darkart_channel)
        file = hikari.File("output.png")
        await channel.send(file)
    except Exception as e:
        print(f"Folgender Fehler ist beim Senden des Bildes aufgetreten: {str(e)}")
        if BotConfig.dev_mode:
            await ctx.author.send("Es gab einen Fehler an meinem Ende.\nKontaktiere Darkyl#6641 sollte dies öfter geschehen.\n(Ich bin im Programmier Modus. Einige Funktionen könnten nicht funktionieren.)")
        else:
            await ctx.author.send("Es gab einen Fehler an meinem Ende.\nKontaktiere Darkyl#6641 sollte dies öfter geschehen.")

#Sends the image in DM's
async def send_image_private(ctx: lightbulb.SlashContext) -> None:
    try:
        file = hikari.File("output.png")
        await ctx.author.send("Hier ist dein Bild!")
        await ctx.author.send(file)
    except Exception as e:
        print(f"Folgender Fehler ist beim Senden des Bildes aufgetreten: {str(e)}")
        if BotConfig.dev_mode:
            await ctx.author.send("Es gab einen Fehler an meinem Ende.\nKontaktiere Darkyl#6641 sollte dies öfter geschehen.\n(Ich bin im Programmier Modus. Einige Funktionen könnten nicht funktionieren.)")
        else:
            await ctx.author.send("Es gab einen Fehler an meinem Ende.\nKontaktiere Darkyl#6641 sollte dies öfter geschehen.")
    await ctx.respond("Das Bild wurde erfolgreich generiert.", flags=hikari.MessageFlag.EPHEMERAL)

#/imagine Command
@bot.command
@lightbulb.option("prompt", "Was soll ich malen?", required=True, type=str | None, max_length=SDConfig.max_prompt_length)
@lightbulb.option("steps", "Qualität des Bildes", required=False, default=SDConfig.default_steps, type=int, min_value=2, max_value=30)
@lightbulb.option("width", "Breite des Bildes (Pixel)", required=False, default=SDConfig.default_width, type=int, min_value=200, max_value=1300)
@lightbulb.option("height", "Höhe des Bildes (Pixel)", required=False, default=SDConfig.default_heigth, type=int, min_value=200, max_value=1300)
@lightbulb.option("private", "Private Bilder werden in den DMs geschickt", required=False, default=False, type=bool)
@lightbulb.option("negative_prompt", "Was soll nicht ins Bild?", required=False, type=str)
@lightbulb.command("imagine", "Generiere Bilder")
@lightbulb.implements(lightbulb.SlashCommand)
async def imagine_command(ctx: lightbulb.SlashContext) -> None:

    if ctx.channel_id != BotConfig.darkart_channel:
        await ctx.respond(f"Das funktioniert nur im <#{BotConfig.darkart_channel}> Kanal.")
        return
    is_private = ctx.options.private
    prompt = ctx.options.prompt
    
    #Unnecessary since Image will be saved with prompt regardles
    #if not is_private:
    #    print(f"Prompt is: {prompt}")

    #Fetching variables 
    negative_prompt = f"{SDConfig.default_negative_prompt}, {ctx.options.negative_prompt}"
    user_name = ctx.author.username.replace(" ", "_")
    user_discriminator = ctx.author.discriminator
    steps = ctx.options.steps
    width = ctx.options.width
    height = ctx.options.height

    #Giving response
    if is_private:
        if BotConfig.dev_mode:
            await ctx.respond("Generiere ein Bild.\nDas Resultat wird in die DM's geschickt.\nBitte warten...\n(Ich bin im Programmier Modus. Einige Funktionen könnten nicht funktionieren.)", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("Generiere ein Bild.\nDas Resultat wird in die DM's geschickt.\nBitte warten...", flags=hikari.MessageFlag.EPHEMERAL)
    else:
        if BotConfig.dev_mode:
            await ctx.respond(f"Generiere ein Bild mit der Eingabe: \n{prompt}.\nBitte warten...\n(Ich bin im Programmier Modus. Einige Funktionen könnten nicht funktionieren.)")
        else:
            await ctx.respond(f"Generiere ein Bild mit der Eingabe: \n{prompt}.\nBitte warten...")
    
    #Calling image generating function
    image_path = await asyncio.create_task(generate_image(user_name, user_discriminator, prompt, is_private, steps, width, height, negative_prompt))
    
    #Sending the image to the user
    if is_private:
        if image_path is not None:
            await send_image_private(ctx)
    else:
        if image_path is not None:
            await send_image(ctx)

if __name__ == "__main__":
    validate_config()

    pf.load_censor_words()

    if BotConfig.dev_mode:
        bot.run(
            status=hikari.Status.ONLINE,
            activity=hikari.Activity(name="I am in Dev Mode!", type=hikari.ActivityType.WATCHING,),
                )
    else:
        bot.run()
