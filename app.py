import os
import json
import gradio as gr
import shutil
from libs.utils import get_data_list,data_path,get_spk_list,load_accent_model,now_dir,synth
from gr_tabs.parse_tab import parse_tab
from gr_tabs.tts_tab import tts_tab
from gr_tabs.settings_tab import settings_tab
from gr_tabs.cover_tab import cover_tab

gr.set_static_paths(paths=[data_path,])

sound_dir = os.path.join(now_dir, "sound")
accentizer = None

def refresh_data(ab_name):
    return {"value": ab_name, "choices": sorted(get_data_list()), "__type__": "update"}

def remove_dataset(ab_name):
    ab_path = os.path.join(now_dir, "data", ab_name)
    gr.Warning(f'Remove Dataset {ab_name}')
    shutil.rmtree(ab_path)
    return {"value": '', "choices": sorted(get_data_list()), "__type__": "update"}, \
            {"visible": False, "__type__": "update"}

def save_drop_dataset_audio(dropbox):
    ab_file = os.path.basename(dropbox)
    ab_name = os.path.splitext(ab_file)[0]
    ab_path = os.path.join(now_dir, "data", ab_name)
    if not os.path.exists(ab_path):
        os.makedirs(ab_path)
    destination_path = os.path.join(ab_path, ab_file)
    if os.path.exists(destination_path):
        os.remove(destination_path)
    shutil.copy(dropbox, destination_path)
    gr.Info("Файл загружен",duration=4)
    return refresh_data(ab_name)

def toggle_tab(ab_path):
    return gr.Tabs(visible=True, selected=0),ab_path

def put_accents(string):
    string = accentizer.process_all(string,'\+\w+|\w+\+\w+')
    return string

def text_to_audio(string, spk, rate=1, noise=None):
    if not synth:
        return {"label": "Модель не загружена!", "__type__": "update"}
    np_audio, sr = synth.synth_audio(string,speaker_id=spk)
    return (sr, np_audio)

tts_models_list = [
    ('Vosk 0.9 (5 голосов)', 9),
    ('Vosk 0.10 (dev. 56 голосов)', 10),
    ('Silero v5 (5 голосов)', 5),
]

accent_models_list = [
    ('RuAccent', 1),
    ('Silero stress', 2),
]

def tts_model_load(ver=10, progress=gr.Progress()):
    progress(0.8, desc="Загрузка модели...")
    synth.load(ver)
    fin_text = "Модель успешно загружена!"
    progress(1.0, desc=fin_text)
    return fin_text, ver

def acc_model_load(ver=1, progress=gr.Progress()):
    global accentizer
    progress(0.8, desc="Загрузка модели...")
    accentizer = load_accent_model(ver)
    fin_text = "Модель успешно загружена!"
    progress(1.0, desc=fin_text)
    return fin_text,ver

def change_tts_model(mver):
    sp_list = get_spk_list(mver)
    speaker = sp_list[0]
    if isinstance(speaker, tuple):
        speaker = sp_list[0][1]
    return (
        {"value": speaker, "choices": sp_list, "__type__": "update"},
        {"interactive": True, "__type__": "update"}, 
        {"interactive": True, "__type__": "update"}
    )

def change_acc_model(mver):
    return {"interactive": True, "__type__": "update"}

custom_theme = gr.themes.ThemeClass.load("themes/argilla.json")

with gr.Blocks(theme=custom_theme, title="🇷🇺") as App:

    tts_state = gr.State()
    acc_state = gr.State()
    with gr.Sidebar():
        tts_sel = gr.Dropdown(
            value='',
            allow_custom_value=True,
            label='Выбрать модель TTS',
            choices=tts_models_list,
            interactive=True,
        )
        tts_status= gr.Textbox(show_label=False, visible=True)
        acc_sel = gr.Dropdown(
            value='',
            allow_custom_value=True,
            label='Расстановка ударений',
            choices=accent_models_list,
            interactive=True,
        )
        acc_status= gr.Textbox(show_label=False, visible=True)

        tts_sel.select(
            tts_model_load,
            inputs=tts_sel,
            outputs=[tts_status,tts_state],
            show_progress_on=tts_status
        )
        acc_sel.select(
            acc_model_load,
            inputs=acc_sel,
            outputs=[acc_status,acc_state],
            show_progress_on=acc_status
        )
    with gr.Tabs():
        with gr.TabItem(label="Demo TTS"):
            with gr.Row():
                spk_sel = gr.Dropdown(
                    value=0,
                    label='Выбрать голос',
                    choices=get_spk_list(),
                    interactive=True,
                )
                speech_rate = gr.Slider(
                    0,
                    3,
                    1,
                    step=0.1,
                    label="Задать скорость",
                    interactive=True,
                )
                noise_lvl = gr.Slider(
                    0,
                    2,
                    0.8,
                    step=0.1,
                    label="Уровень шума",
                    interactive=True,
                )
            with gr.Row():
                text_input = gr.Textbox(label='Текст',lines=2, placeholder="Введите текст для озвучки", interactive=True,)
                audio_output = gr.Audio(interactive=False,show_download_button=False)
            with gr.Row():
                accent_button = gr.Button("Проставить ударения", interactive=False)
                tts_button = gr.Button("Преобразовать в речь", interactive=False)

            accent_button.click(
                put_accents,
                inputs=text_input,
                outputs=text_input
            )
            tts_button.click(
                text_to_audio,
                inputs=[text_input,spk_sel,speech_rate,noise_lvl],
                outputs=audio_output
            )
        with gr.TabItem("Fb2TTS",interactive=False) as fb2tts_tab:
            ab_state= gr.State()
            with gr.Row():
                ab_path = gr.Dropdown(
                    value='',
                    show_label=False,
                    allow_custom_value=True,
                    choices=get_data_list(),
                    interactive=True,
                )
                rm_dataset = gr.Button("❌ Удалить АК")
                upload_text_file = gr.UploadButton("Загрузить файл", file_count="single", file_types=[".fb2", ".txt"])
            with gr.Tabs(visible=False) as tabs:
                cover_tab(ab_path,ab_state)
                parse_tab(ab_path,acc_state)
                tts_tab(ab_path,tts_state)

            upload_text_file.upload(
                fn=save_drop_dataset_audio,
                inputs=upload_text_file,
                outputs=[ab_path],
            ).then(
                toggle_tab,
                inputs=ab_path,
                outputs=[tabs,ab_state]
            )

            rm_dataset.click(
                remove_dataset,
                inputs=ab_path,
                outputs=[ab_path,tabs]
            )

            ab_path.select(
                toggle_tab,
                inputs=ab_path,
                outputs=[tabs,ab_state]
            )

        with gr.TabItem("Настройки"):
            settings_tab()

    tts_state.change(
        change_tts_model,
        inputs=tts_state,
        outputs=[spk_sel,fb2tts_tab,tts_button]
    )
    acc_state.change(
        change_acc_model,
        inputs=acc_state,
        outputs=accent_button
    )

App.launch(
    share=False,
    server_name="0.0.0.0",
    allowed_paths=[sound_dir],
    favicon_path='libs/vosk.ico'
)