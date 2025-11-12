import os
import re
import random
import tempfile
import zipfile
import gradio as gr
import pandas as pd
from lxml import etree
import concurrent.futures
import threading
from functools import partial
from pydub import effects, AudioSegment
from libs.utils import get_spk_list, convert, synth

now_dir = os.getcwd()
data_path = os.path.join(now_dir, "data")

stop_text_to_sp = False

def tts(ab_path, repl, spk_sel, sch_r, spk2_sel, sch_r2, back_sound_sel, mp3_bitrate, progress=gr.Progress()):
    work_dir = os.path.join(data_path, ab_path)
    xml_path = os.path.join(work_dir, 'xml')
    mp3_path = os.path.join(work_dir, 'mp3')
    if not os.path.exists(mp3_path) and mp3_path is not None:
        os.makedirs(mp3_path)

    global stop_text_to_sp
    stop_text_to_sp = False
    args = lambda: None
    args.debug = 0

    files = os.listdir(xml_path)
    files = [x.split('.')[0] for x in files]
    
    for file in progress.tqdm(sorted(files, key=float), desc="Обработка файлов"):
        if os.path.exists(f'{mp3_path}/{file}.mp3') and not repl:
            gr.Warning(f'{file}.mp3 уже есть', duration=3)
            continue

        root = etree.parse(f'{xml_path}/{file}.xml').getroot()
        out_audio = AudioSegment.empty()
        autor = root.get('autor')
        album = root.get('album')
        gender = root.get('gender')
        default_speaker = spk_sel
        sub_speaker = 3
        if gender and gender == 'femn':
            default_speaker = 2

        tasks = []
        lines_list = list(root)
        
        for i, line in enumerate(lines_list):
            if stop_text_to_sp:
                stop_text_to_sp = False
                yield get_files_list(ab_path), "Выполнение прервано пользователем"
                return
            
            use_speaker = spk_sel
            speech_rate = sch_r
            ntree = etree.Element('speak')
            pros = etree.Element('prosody')
            
            if line.tag == 'cite' or line.tag == 'title':
                pros = etree.Element('prosody')
                pros.text = line.text
                ntree.append(pros)
            elif line.text:
                pros.text = line.text
                ntree.append(pros)
            else:
                ntree.append(line)

            if line.tag == 'cite':
                use_speaker = spk2_sel
                speech_rate = sch_r2
            
            # Для звуковых файлов и пауз - синхронная обработка
            if line.tag == 'sound':
                audio = AudioSegment.from_wav(f'sound/events/{line.get("val")}.wav')
                audio = effects.normalize(audio)
                tasks.append(('audio', audio, line))
            elif line.tag == 'break':
                slt = int(line.get('time')) * 100
                audio = AudioSegment.silent(duration=slt)
                tasks.append(('audio', audio, line))
            elif line.text:
                tasks.append(('text', line.text, use_speaker, speech_rate, line))
            else:
                tasks.append(('empty', None, None, None, line))

        processed_audio_segments = [None] * len(tasks)
        
        def process_text_task(index, text, speaker, rate):
            if stop_text_to_sp:
                return None
                
            if args.debug != 0 and text:
                print(text)
            
            np_audio, sr = synth.synth_audio(
                text,
                speaker,
                rate
            )
            audio = AudioSegment(
                np_audio.tobytes(),
                frame_rate=sr,
                sample_width=2,
                channels=1
            )
            return index, effects.normalize(audio)

        text_tasks = [(i, task[1], task[2], task[3]) for i, task in enumerate(tasks) if task[0] == 'text']
        
        if text_tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                future_to_index = {
                    executor.submit(process_text_task, i, text, speaker, rate): i 
                    for i, text, speaker, rate in text_tasks
                }
                
                completed = 0
                total_text_tasks = len(text_tasks)
                
                for future in progress.tqdm(concurrent.futures.as_completed(future_to_index), 
                                          total=total_text_tasks, 
                                          desc=f"Синтез аудио {file}.xml"):
                    if stop_text_to_sp:
                        executor.shutdown(wait=False)
                        stop_text_to_sp = False
                        yield get_files_list(ab_path), "Выполнение прервано пользователем"
                        return
                        
                    try:
                        result = future.result()
                        if result:
                            index, audio = result
                            processed_audio_segments[index] = audio
                        completed += 1
                    except Exception as e:
                        print(f"Ошибка при обработке аудио: {e}")
                        completed += 1

        for i, task in enumerate(progress.tqdm(tasks, desc=f"Сборка аудио {file}.xml")):
            if stop_text_to_sp:
                stop_text_to_sp = False
                yield get_files_list(ab_path), "Выполнение прервано пользователем"
                return
                
            line = task[-1]
            
            if task[0] == 'audio':
                audio = task[1]
            elif task[0] == 'text':
                audio = processed_audio_segments[i]
                if audio is None:
                    continue
            else:
                continue

            if line.tag == 'cite' and line.get('position') == 'start':
                pr_audio = AudioSegment.from_wav('sound/pause/cite.wav')
                pr_audio = effects.normalize(pr_audio)
                audio = pr_audio + audio
                
            if line.tag == 'empty-line':
                pr_audio = AudioSegment.from_wav('sound/pause/empty.wav')
                pr_audio = effects.normalize(pr_audio)
                audio = pr_audio + audio
                
            if (line.getprevious() is None and line.tag != 'title' and line.tag != 'empty-line' \
                and line.tag != 'sound' and line.tag != 'break' and back_sound_sel) \
                or (line.tag == 'title' and back_sound_sel):
                pr_audio = AudioSegment.from_wav(f'sound/back/{back_sound_sel}')
                duration = pr_audio.duration_seconds
                kk = duration // 12
                st_poz = random.randint(0, kk) * 1000
                pr_audio = pr_audio[st_poz:st_poz + 12000]
                pr_audio = pr_audio.fade_out(4000)
                pr_audio = pr_audio.fade_in(4000)
                pr_audio = pr_audio - 5
                audio = pr_audio.overlay(audio, position=4000, gain_during_overlay=-6.0)
            
            out_audio = out_audio + audio

        out_audio.export(
            f'{mp3_path}/{file}.mp3',
            format='mp3',
            bitrate=f'{mp3_bitrate}',
            cover=f'{work_dir}/cover.jpg',
            tags={
                'artist': autor,
                'title': f'Глава {file}',
                'track': f'{file}',
                'album': album
            }
        )
        yield get_files_list(ab_path), f'Обработан файл: {file}.xml'
    
    return get_files_list(ab_path), gr.Label(visible=False)

def get_files_list(ab_name):
    d_path = os.path.join(now_dir, 'data', ab_name, 'mp3')
    df = pd.DataFrame(columns=['Audio', 'Имя файла', 'Размер', 'Продолжительность'])
    if os.path.exists(d_path):
        files = os.listdir(d_path)
        files=[x.split('.')[0] for x in files]
        for file_name in sorted(files, key=float):
            full_path = os.path.join(d_path, f"{file_name}.mp3")
            audio = AudioSegment.from_file(full_path, format="mp3")
            size = os.path.getsize(full_path)
            size_in_mb = round(size / (1024 * 1024), 2)
            new_row = {
                "Audio": f'<audio controls src="/gradio_api/file=data/{ab_name}/mp3/{file_name}.mp3"></audio>',
                "Имя файла": f"{file_name}.mp3",
                "Размер": f"{size_in_mb} Mb.",
                "Продолжительность": convert(audio.duration_seconds)
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df

def create_zip_archive(ab_path):
    mp3_dir = os.path.join(data_path, ab_path, 'mp3')
    if not os.path.exists(mp3_dir):
        raise gr.Error(f"Папка с файлами не найдена!")
    
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        zip_filename = tmp.name
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(mp3_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = f'{ab_path}/{file}'
                    zipf.write(file_path, arcname)
        
        return {"visible": True, "value": zip_filename,"__type__": "update"}
    
    except Exception as e:
        if os.path.exists(zip_filename):
            os.unlink(zip_filename)
        raise gr.Error(f"Ошибка: {str(e)}")

def enable_status():
    return {"visible": True, "__type__": "update"}

def snd_list():
    snd_path = os.path.join(now_dir, "sound", 'back')
    return  {"value": '', "choices": sorted(os.listdir(snd_path)), "__type__": "update"}

def del_file(filename, ab_name):
    gr.Info(f'Remove {os.path.basename(filename)}', duration=2)
    os.remove(filename)
    return get_files_list(ab_name)

def sel_file(data: gr.SelectData, ab_path):
    mp3_dir = os.path.join(data_path, ab_path, 'mp3')
    return {"interactive": True, "__type__": "update"}, f'{mp3_dir}/{data.value}'

def stop_tts():
    global stop_text_to_sp
    stop_text_to_sp = True
    return "Прерываем выполнение..."

def change_tts_model(mver):
    sp_list = get_spk_list(mver)
    speaker = sp_list[0]
    if isinstance(speaker, tuple):
        speaker = sp_list[0][1]
    return (
        {"value": speaker, "choices": sp_list, "__type__": "update"},
        {"value": speaker, "choices": sp_list, "__type__": "update"}
    )

def tts_tab(ab_path, tts_state):
    with gr.Tab(label = "Создать АК", id=2) as tts_tab:
        with gr.Row():
            spk_sel = gr.Dropdown(
                    value='',
                    label='Выбрать основной голос',
                    choices=[''],
                    interactive=True,
                )
            sp_rate = gr.Slider(
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
            spk2_sel = gr.Dropdown(
                    value='',
                    label='Выбрать голос для цитат',
                    choices=[''],
                    interactive=True,
                )
            sp_rate2 = gr.Slider(
                0,
                3,
                1,
                step=0.1,
                label="Задать скорость",
                interactive=True,
            )
            noise_lvl2 = gr.Slider(
                0,
                2,
                0.8,
                step=0.1,
                label="Уровень шума",
                interactive=True,
            )
        with gr.Row():
            back_sound_sel = gr.Dropdown(
                    value='',
                    allow_custom_value=True,
                    label='Выбрать музыку для оглавлений',
                    choices=[''],
                    interactive=True,
                )
            bitrate = gr.Slider(
                24,
                256,
                96,
                step=2,
                label="Задать битрейт аудио",
                interactive=True,
            )
        with gr.Row():
            repl = gr.Checkbox(label="Переписать")
            tts_button = gr.Button("🟢 TTS")
            stop_btn = gr.Button("🚫 Прервать")
        with gr.Row():
            cur_file = gr.State()
            pr_status= gr.Textbox(show_label=False, visible=False)
        with gr.Row():
            df_output = gr.DataFrame(
                headers=['Audio', 'Имя файла', 'Размер', 'Продолжительность'],
                interactive=False,
                datatype=["html", "str", "str", "str"],
                column_widths=['320px'],
            )
        del_btn = gr.Button("❌ Удалить файл", interactive=False)
        create_arh_btn = gr.Button("Создать архив с АК")
        download_btn = gr.DownloadButton(
            "📥 Скачать архив с АК",
            value=None,
            variant="primary",
            visible=False
        )

    download_btn.click(
        fn=lambda: gr.DownloadButton(visible=False),
        outputs=download_btn
    )
    create_arh_btn.click(
        create_zip_archive,
        inputs=ab_path,
        outputs=download_btn
    )
    df_output.select(
        sel_file,
        inputs=ab_path,
        outputs=[del_btn, cur_file]
    )
    tts_button.click(
        enable_status,
        outputs=pr_status
    ).then(
        fn=tts,
        inputs=[ab_path,repl,spk_sel,sp_rate,spk2_sel,sp_rate2,back_sound_sel,bitrate],
        outputs=[df_output, pr_status],
        show_progress_on=pr_status
    )
    stop_btn.click(
        stop_tts,
        outputs=pr_status,
        queue=False
    )
    del_btn.click(
        del_file,
        inputs=[cur_file,ab_path],
        outputs=[df_output]
    )
    tts_tab.select(
        get_files_list,
        inputs=ab_path,
        outputs=df_output
    ).then(
        snd_list,
        outputs=back_sound_sel
    )
    tts_state.change(
        change_tts_model,
        inputs=tts_state,
        outputs=[spk_sel,spk2_sel]
    )
