import sublime
import sublime_plugin
import json
import os
from threading import Thread
import logging
import urllib.request
import urllib.error
import base64

# Constants
SETTINGS_FILE = "LLMPlugin.sublime-settings"
API_KEY_OPENAI = "openai_api_key"
API_KEY_ANTHROPIC = "anthropic_api_key"

# Set up logging
logging.basicConfig(filename='llm_plugin.log', level=logging.INFO)
logger = logging.getLogger(__name__)

def encrypt(key):
    return base64.b64encode(key.encode()).decode()

def decrypt(encrypted_key):
    return base64.b64decode(encrypted_key.encode()).decode()

class LanguageModelCommand(sublime_plugin.TextCommand):
    def run(self, edit, action, prompt=None):

        settings = sublime.load_settings(SETTINGS_FILE)
        selected_provider = settings.get("selected_provider", "openai")

        if selected_provider == "openai":
            encrypted_api_key = settings.get(API_KEY_OPENAI)
            api_key = decrypt(encrypted_api_key) if encrypted_api_key else None            
            api_url = "https://api.openai.com/v1/chat/completions"
            model = settings.get("openai_model", "gpt-3.5-turbo")
        elif selected_provider == "anthropic":
            encrypted_api_key = settings.get(API_KEY_ANTHROPIC)
            api_key = decrypt(encrypted_api_key) if encrypted_api_key else None            
            api_url = "https://api.anthropic.com/v1/messages"
            model = settings.get("anthropic_model", "claude-2")
        else:
            sublime.error_message(f"Unknown LLM: {selected_provider}")
            return

        if not api_key:
            sublime.error_message(f"API key for {selected_provider} is not set. Please set it in the settings.")
            return

        selection = self.view.sel()
        if len(selection) > 0:
            for region in selection:
                if not region.empty():
                    text = self.view.substr(region)

                    thread = Thread(target=self.process_text, args=(text, action, api_key, api_url, region, selected_provider, model, prompt))
                    thread.start()
                    self.show_loading_indicator(thread)
                else:
                    sublime.status_message("No text selected")
        else:
            sublime.status_message("No selection found")

    def process_text(self, text, action, api_key, api_url, region, selected_provider, model, prompt=None):
        if prompt is None:
            prompt = self.get_prompt(action, text)            
        
        if selected_provider == "openai":
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
        elif selected_provider == "anthropic":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": f"{api_key}",
                "max_tokens": 1024
            }

            data = {                
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens" : 1024,
                "system" : "You are an English language expert.",                
                "messages": [{"role": "user", "content": [{ "type" : "text", "text" : prompt}]}]
            }                  
    
        try:
            print(data)
            req = urllib.request.Request(api_url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')            
            
            with urllib.request.urlopen(req) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                print(response_data)
                if selected_provider == "openai":
                    result = response_data["choices"][0]["message"]["content"]
                elif selected_provider == "anthropic":
                    result = response_data["content"][0]["text"]  
                sublime.set_timeout(lambda: self.replace_text(region, result), 0)
                # print(result)
        except urllib.error.URLError as e:
            error_message = f"API request failed: {str(e)}"
            logger.error(error_message)
            sublime.error_message(error_message)
        except KeyError as e:
            error_message = f"Unexpected API response format: {str(e)}"
            logger.error(error_message)
            sublime.error_message(error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {str(e)}"
            logger.error(error_message)
            sublime.error_message(error_message)

    def replace_text(self, region, new_text):
        self.view.run_command("replace_text", {"region": (region.a, region.b), "text": new_text})

    def get_prompt(self, action, text):
        prompts = {
            "rewrite_casual": f"Rewrite the following text in a casual tone. Use Australian Spelling. Respond only with the updated text.: {text}",
            "rewrite_professional": f"Rewrite the following text in a professional tone. Use Australian Spelling. Respond only with the updated text.: {text}",
            "summarise": f"Summarise the following text. Use Australian Spelling. Respond only with the updated text.: {text}",
            "expand": f"Expand on the following text. Use Australian Spelling. Respond only with the updated text.: {text}",
            "paraphrase": f"Paraphrase the following text. Use Australian Spelling. Respond only with the updated text.: {text}",
            "correct_grammar": f"Correct the grammar in the following text. Use Australian Spelling. Respond only with the updated text.: {text}",
            "dynamic_prompt": text
        }
        return prompts.get(action, f"Process the following text. : {text}")

    def show_loading_indicator(self, thread):
        i = 0
        frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        while thread.is_alive():
            sublime.status_message(f"Processing {frames[i % len(frames)]}")
            sublime.set_timeout(lambda: None, 100)
            i += 1
        sublime.status_message("Processing complete")

class ReplaceTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, region, text):
        self.view.replace(edit, sublime.Region(region[0], region[1]), text)

class RewriteCasualCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("language_model", {"action": "rewrite_casual"})

class RewriteProfessionalCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("language_model", {"action": "rewrite_professional"})

class SummariseCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("language_model", {"action": "summarise"})

class ExpandCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("language_model", {"action": "expand"})

class ParaphraseCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("language_model", {"action": "paraphrase"})

class CorrectGrammarCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command("language_model", {"action": "correct_grammar"})

class DynamicPromptResponseCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().show_input_panel("Enter your prompt:", "", self.on_done, None, None)

    def on_done(self, prompt):
        self.view.run_command("language_model", {"action": "dynamic_prompt", "prompt": prompt})

class SetApiKeyCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        settings = sublime.load_settings(SETTINGS_FILE)
        options = ["OpenAI API Key", "Anthropic API Key"]
        
        def on_done(index):
            if index != -1:
                key_type = API_KEY_OPENAI if index == 0 else API_KEY_ANTHROPIC
                self.prompt_for_api_key(key_type)
        
        sublime.active_window().show_quick_panel(options, on_done)

    def prompt_for_api_key(self, key_type):
        def on_done(api_key):
            if api_key:
                encrypted_key = encrypt(api_key)
                settings = sublime.load_settings(SETTINGS_FILE)
                settings.set(key_type, encrypted_key)
                sublime.save_settings(SETTINGS_FILE)
                sublime.status_message(f"{key_type} updated successfully")
            else:
                sublime.error_message("API key cannot be empty")

        sublime.active_window().show_input_panel(f"Enter {key_type}:", "", on_done, None, None)

class SelectModelCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        settings = sublime.load_settings(SETTINGS_FILE)
        selected_provider = settings.get("selected_provider", "openai")
        
        if selected_provider == "openai":
            options = ["gpt-4o-mini", "gpt-4o", "gpt-4"]
            setting_key = "openai_model"
        elif selected_provider == "anthropic":
            options = ["claude-3.5-sonnet", "claude-3-sonnet", "claude-3-opus", "claude-3-haiku"]
            setting_key = "anthropic_model"
        else:
            sublime.error_message(f"Unknown LLM: {selected_provider}")
            return

        def on_done(index):
            if index != -1:
                settings.set(setting_key, options[index])
                sublime.save_settings(SETTINGS_FILE)
                sublime.status_message(f"Selected model: {options[index]}")
        
        sublime.active_window().show_quick_panel(options, on_done)

class SwitchProviderCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        settings = sublime.load_settings(SETTINGS_FILE)
        options = ["OpenAI", "Anthropic"]
        
        def on_done(index):
            if index != -1:
                new_llm = options[index].lower()
                settings.set("selected_provider", new_llm)
                sublime.save_settings(SETTINGS_FILE)
                sublime.status_message(f"Switched to {options[index]} LLM")
        
        sublime.active_window().show_quick_panel(options, on_done)

def plugin_loaded():
    settings = sublime.load_settings(SETTINGS_FILE)
    if not settings.has("selected_provider"):
        settings.set("selected_provider", "openai")
    if not settings.has("openai_model"):
        settings.set("openai_model", "gpt-3.5-turbo")
    if not settings.has("anthropic_model"):
        settings.set("anthropic_model", "claude-2")
    sublime.save_settings(SETTINGS_FILE)

def plugin_unloaded():
    pass
