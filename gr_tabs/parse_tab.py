import os
import re
import time
import gradio as gr
import pandas as pd
from lxml import etree
from libs.utils import now_dir,data_path,get_ab_name,set_args
from libs.tts_preprocessor import preprocess,sound_check,garbage
from libs.fix_fb2 import adopt_for_parse
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

def parse_section(tags):

    p = etree.Element('line')

    if tags.text and tags.get('lang') is None:
        sndml = sound_check(tags.text)
        if sndml:
            sndml = etree.fromstring(sndml)
            for tt in sndml:
                if tt.text or tt.tag == 'sound':
                    p.append(tt)
        else:
            tags.text = preprocess(tags.text)
            p.append(tags)
    else:
        p.append(tags)
    return p

def male_fem(tags):
    male = 0
    female = 0
    if tags.text:
        cl_text = garbage(tags.text)
        cl_text = re.sub( ',|\!|\?|\.', ' ', cl_text)
        for item in cl_text.split(' '):
            ch_word = item.strip()
            p = morph.parse(ch_word)[0]
            if p.tag.POS == 'VERB' and p.tag.tense == 'past':
                if p.tag.gender == 'masc':
                    male += 1
                elif p.tag.gender == 'femn':
                    female += 1
    if male > female:
        return 1
    if male < female:
        return -1
    return 0

def split(arr, size):
    arrs = []
    while len(arr) > size:
        pice = arr[:size]
        arrs.append(pice)
        arr   = arr[size:]
    arrs.append(arr)
    return arrs

def parse_fb2(ab_path, repl, mltlg, progress=gr.Progress()):

    df = pd.DataFrame(columns=["Name"])
    work_dir = os.path.join(data_path, ab_path)
    xml_path = os.path.join(work_dir, 'xml')
    if not os.path.exists(xml_path) and xml_path is not None:
        os.makedirs(xml_path)

    args = lambda: None
    args.name = f'{work_dir}/{ab_path}.fb2'
    args.work_dir = work_dir
    args.multilang = mltlg
    args.debug = 0
    args.replace = repl
    args.tag = None
    set_args(args)

    title = 1
    desc = adopt_for_parse(args)
    root = desc['body']

    first_name = desc['first_name']
    annotation = desc['annotation']
    last_name = desc['last_name']
    book_title = desc['book_title']
    bt = etree.Element('p')
    bt.text = preprocess(f'{first_name} {last_name}. {book_title}.')

    for i, elem in enumerate(progress.tqdm(root.findall("section"), desc="Обработка файлов")):
    #for i, elem in enumerate(root.findall("section")):
        sec_title = elem.find('title')

        if elem.findall("section"):
            s_title = 1
            for sect in elem.findall("section"):
                if len(sect) > 0:
                    ntree = etree.Element('speak', autor=f'{first_name} {last_name}', album=f'{book_title}')
                    if title == 1 and s_title == 1:
                        ntree.append( etree.Element('break', time='20') )
                        ntree.append(bt)
                        ntree.append( etree.Element('break', time='5') )
                        if annotation is not None:
                            for txt in annotation:
                                ann = etree.Element('p')
                                ann.text = preprocess(txt.text)
                                ntree.append(ann)
                    if s_title == 1 and sec_title is not None and sect.find('title') is None:
                        sec_title.text = preprocess(sec_title.text)
                        ntree.append(sec_title)                    
                    if os.path.exists(f'{xml_path}/{title}_{s_title}.xml') and not args.replace:
                        print(f'{title}_{s_title}.xml File exist!')
                    else:
                        txt_male = 0
                        for tags in sect:
                            txt_male = txt_male + male_fem(tags)
                            if tags.tag == 'title' and s_title == 1 and sec_title is not None:
                                tags.text = sec_title.text + '. ' + tags.text
                            for ts in parse_section(tags):
                                ntree.append(ts)
                                if args.debug == 2: etree.dump(ts)
                        if txt_male >= 0:
                            ntree.set('gender','masc')
                        else:
                            ntree.set('gender','femn')
                        tree = etree.ElementTree(ntree)
                        tree.write(f'{xml_path}/{title}_{s_title}.xml', encoding='utf-8', pretty_print=True)
                    s_title += 1
            title += 1
        else:
            if elem.tag == 'section' and len(elem) > 0:
                ntree = etree.Element('speak', autor=f'{first_name} {last_name}', album=f'{book_title}')
                if title == 1:
                        ntree.append( etree.Element('break', time='20') )
                        ntree.append(bt)
                        ntree.append( etree.Element('break', time='5') )
                        if annotation is not None:
                            for txt in annotation.findall("p"):
                                ann = etree.Element('p')
                                ann.text = preprocess(txt.text)
                                ntree.append(ann)
                
                if os.path.exists(f'{xml_path}/{title}.xml') and not args.replace:
                    gr.Info(f'{title}.xml File exist!', duration=3)
                else:
                    txt_male = 0
                    for tags in elem:
                        txt_male = txt_male + male_fem(tags)
                        for ts in parse_section(tags):
                            ntree.append(ts)
                            if args.debug == 'all': etree.dump(ts)
                    if txt_male >= 0:
                        ntree.set('gender','masc')
                    else:
                        ntree.set('gender','femn')
                    ntree = etree.ElementTree(ntree)
                    ntree.write(f'{xml_path}/{title}.xml', encoding='utf-8', pretty_print=True)
            new_row = {
                "Name": f'{title}.xml',
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            title += 1
        yield df, ''

    progress(1, desc="Всё причесали!")
    return df, gr.Label(visible=False)

def enable_status():
    return {"visible": True, "__type__": "update"}

def save_xml(content, filename):
    if not content:
        gr.Warning("Ошибка: содержимое пустое", duration=5)
    try:
        # Проверяем, что XML корректен перед сохранением
        etree.fromstring(content)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        gr.Info(f"Файл успешно сохранён как {filename}", duration=5)
    except Exception as e:
        gr.Warning(f"Ошибка сохранения XML: {str(e)}", duration=5)

def show_file_content(data: gr.SelectData, ab_path):
    xml_dir = os.path.join(data_path, ab_path, 'xml')
    
    try:
        with open(f'{xml_dir}/{data.value}', "r", encoding="utf-8") as f:
            content = f.read()  # Читаем первые 2000 символов
        return content, {"interactive": True, "__type__": "update"}, f'{xml_dir}/{data.value}'
    except Exception as e:
        return f"Ошибка: {str(e)}"

def get_files_list(ab_name):
    d_path = os.path.join(now_dir, "data", ab_name, 'xml')
    df = pd.DataFrame(columns=["Name"])
    if os.path.exists(d_path):
        files = os.listdir(d_path)
        files=[x.split('.')[0] for x in files]
        for file_name in sorted(files, key=float):
            full_path = os.path.join(d_path, f"{file_name}.xml")
            size = os.path.getsize(full_path)
            new_row = {
                "Name": f"{file_name}.xml",
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, ''

def del_file(filename, ab_name):
    gr.Info(f'Remove {os.path.basename(filename)}', duration=2)
    os.remove(filename)
    return get_files_list(ab_name),''

def parse_tab(ab_path):
    with gr.Tab("Анализ", id=1) as pr_tab:
        with gr.Row():
            profanity = gr.Checkbox(label="Запикать мат")
            gender = gr.Checkbox(label="Определение пола")
            multilang = gr.Checkbox(label="Несколько языков", interactive=False)
            snd_ef = gr.Checkbox(label="Озвучить ППББ")
        with gr.Row():
            repl = gr.Checkbox(label="Переписать")
            parse_button = gr.Button("Парсить FB2")
        with gr.Row():
            cur_file = gr.State()
            pr_status= gr.Textbox(show_label=False, visible=False)
        with gr.Row():
            with gr.Column(scale=1):
                df_output = gr.DataFrame(
                    headers=["Name"],
                    interactive=False,
                    datatype=["str"],
                    max_height=720
                )
                del_btn = gr.Button("❌ Удалить файл", interactive=False)
            with gr.Column(scale=7):
                file_content = gr.Code(
                    label="Содержимое файла",
                    language="html",
                    interactive=True,
                    lines=30,
                    max_lines=40
                )
                save_btn = gr.Button("📝 Сохранить изменения")
        
        parse_button.click(
            enable_status,
            outputs=pr_status
        ).then(
            fn=parse_fb2,
            inputs=[ab_path,repl,multilang],
            outputs=[df_output, pr_status],
            show_progress_on=pr_status
        )
        df_output.select(
            fn=show_file_content,
            inputs=ab_path,
            outputs=[file_content, del_btn, cur_file]
        )
        save_btn.click(
            fn=save_xml,
            inputs=[file_content, cur_file],
            #outputs=output_message
        )
        del_btn.click(
            del_file,
            inputs=[cur_file,ab_path],
            outputs=[df_output, file_content]
        )

    pr_tab.select(
        get_files_list,
        inputs=ab_path,
        outputs=[df_output,file_content]
    )
