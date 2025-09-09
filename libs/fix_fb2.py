import os
import re
import base64
import pymorphy3

from lxml import etree
from libs.utils import add_text_cover, word_dict
from libs.tts_preprocessor import preprocess

morph = pymorphy3.MorphAnalyzer()
list_of_snd = word_dict['list_of_snd']

def split(arr, size):
    arrs = []
    while len(arr) > size:
        pice = arr[:size]
        arrs.append(pice)
        arr   = arr[size:]
    arrs.append(arr)
    return arrs

def parse_section(tags,args):
    p = etree.Element('line')
    gnd = 0
    if tags.text and tags.get('lang') is None:
        if args.snd_ef and (sndml := sound_check(tags.text)):
            for tt in etree.fromstring(sndml):
                if tt.text or tt.tag == 'sound':
                    p.append(tt)
        else:
            tags.text = preprocess(tags.text)
            p.append(tags)
    elif args.gender:
        p.set('gender', f'{male_fem(tags)}')
    else:
        p.append(tags)
    if args.debug == 2: etree.dump(tags)
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
    if male >= female:
        return 1
    else:
        return -1

def sound_check(string):
    snd =  '|'.join(list_of_snd.keys())
    x = re.findall(rf'\b({snd})', string)
    if len(x) >=1:
        out_string = '<snd><p>'
        string = re.sub(rf'\b({snd})(\W+|\W)', r'\1 ', string)
        for word in string.split():
            if list_of_snd.get(word):
                out_string = out_string + f'</p><sound val="{list_of_snd[word]}"/><p>'
            else:
                out_string = out_string + preprocess(word) + ' '
        out_string = out_string + '</p></snd>'
        return out_string

    return False

def lang_check(string):
    lang = 'ru'
    if re.search('[a-zA-Z]', string) and not re.search('[а-яА-Я]', string):
        lang = 'en'    
    return lang

def adopt_for_parse(args):
    parser = etree.XMLParser(remove_blank_text=True,ns_clean=True,strip_cdata=True)
    root = etree.parse(args.name,parser).getroot()

    etree.strip_tags(root, '{*}strong', '{*}stanza', '{*}epigraph', '{*}sup')
    etree.cleanup_namespaces(root)

    notes = root.findall("body[@name='notes']/section", namespaces=root.nsmap)
    note_list = {}
    if len(notes) > 0:
        for nt in notes:
            etree.strip_tags(nt, '{*}strong','{*}emphasis', '{*}sup')
            nts = ''
            for text in nt.itertext(tag='{*}p'):
                if re.search('[а-яА-Яa-zA-Z]', text):
                    nts = nts + ' ' + text
            note_list[nt.get('id')] = nts

    for elem in root.iter():
        elem.tag = etree.QName(elem).localname
        if elem.tag == 'section':
            etree.strip_elements(elem,'{*}image')
            if len(list(elem)) > 400:
                if args.tag:
                    args.tag = re.sub('\|', '', args.tag)
                    newsect = etree.Element('section')
                    for pp in list(elem):
                        if pp.text != args.tag:
                            newsect.append(pp)
                        elif pp.text == args.tag:
                            elem.addprevious(newsect)
                            newsect = etree.Element('section')
                            parent=pp.getparent()
                            parent.remove(pp)
                else:
                    for cut_elem in split(elem, 250):
                        newsect = etree.Element('section')
                        for pp in list(cut_elem):
                            newsect.append(pp)
                        elem.addprevious(newsect)              

                parent=elem.getparent()
                parent.remove(elem)

    for elem in root.iter(tag='subtitle'):
        elem.tag = 'p'

    for elem in root.iter(tag='cite'):
        if len(elem) > 0:
            for sel in list(elem):
                new_cite = etree.Element('cite')
                new_cite.text = sel.text
                elem.addprevious(new_cite)
            parent=elem.getparent()
            parent.remove(elem)

    for elem in root.iter(tag='p'):
        elem.tag = etree.QName(elem).localname
        etree.strip_elements(elem,'image')

        if len(list(elem)) == 0:
            if elem.text:
                if not re.search('[а-яА-Яa-zA-Z0-9]', elem.text):
                    parent=elem.getparent()
                    parent.replace(elem,etree.Element('empty-line'))
            elif not elem.text:
                parent=elem.getparent()
                parent.replace(elem,etree.Element('empty-line'))
        elif len(list(elem)) > 0:
            parent=elem.getparent()
            if elem.text:
                etree.strip_tags(elem, 'emphasis', 'strong','stanza', 'sup')
                pg = etree.Element('p')
                pg.text = elem.text
                elem.addprevious(pg)
                for sel in list(elem):
                    if etree.QName(sel).localname == 'a':
                        new_cite = etree.Element('cite')
                        note = sel.get('{http://www.w3.org/1999/xlink}href')
                        if re.search('http', note):
                            pg.text = pg.text + ' ' + sel.text
                            if sel.tail:
                                pg.text = pg.text + ' ' + sel.tail
                        else:
                            new_cite.text = note_list[note[1:]]
                            elem.addprevious(new_cite)
                            if sel.tail:
                                txtt = etree.Element('p')
                                txtt.text = sel.tail
                                elem.addprevious(txtt)
            else:
                for sel in list(elem):
                    if etree.QName(sel).localname == 'emphasis':
                        new_cite = etree.Element('cite')
                        new_cite.text = sel.text
                        elem.addprevious(new_cite)
            parent.remove(elem)

    for elem in root.iter(tag='p'):
        if elem.text:
           # elem.text = garbage(elem.text)
            if len(elem.text) > 400:
                txtarr = elem.text.split('.')
                txtarr = list(filter(lambda i: i != '', txtarr))
                for txt in txtarr:
                    if not re.search('[а-яА-Яa-zA-Z0-9]', txt):
                        continue
                    pg = etree.Element('p')
                    pg.text = txt.lstrip() + '.'
                    if lang_check(pg.text) == 'en' and args.multilang:
                        pg.set('lang', 'en')
                    elem.addprevious(pg)
                parent=elem.getparent()
                parent.remove(elem)
            else:
                if lang_check(elem.text) == 'en' and args.multilang:
                    elem.set('lang', 'en')

    for elem in root.iter(tag='title'):
        elem.tag = etree.QName(elem).localname
        elem.text = ''
        for p_st in list(elem):
            if p_st.text is not None:
                elem.text = elem.text + p_st.text + '. '
        etree.strip_elements(elem, 'empty-line','p')

    for elem in root.iter(tag='empty-line'):
        if elem.getnext() is not None and elem.getnext().tag == 'empty-line':
            parent=elem.getparent()
            parent.remove(elem)
    
    for elem in root.iter('poem','text-author'):
        etree.strip_tags(elem, '{*}emphasis')
        if etree.QName(elem).localname == 'text-author':
            elem.tag='cite'
            elem.text = 'автор ' + elem.text
        elif elem.text is not None:
            print(etree.QName(elem).localname)
            elem.tag='cite'
        else:
            for sel in list(elem):
                sel.tag = etree.QName(sel).localname
                new_cite = etree.Element('cite')
                if sel.tag =='v':
                    new_cite.text = sel.text
                    elem.addprevious(new_cite)
            parent=elem.getparent()
            parent.remove(elem)
    
    
    for elem in root.iter(tag='cite'):
        if elem.text is not None and len(elem.text) > 400:
            txtarr = elem.text.split('.')
            txtarr = list(filter(lambda i: i != '', txtarr))
            for txt in txtarr:
                if not re.search('[а-яА-Яa-zA-Z0-9]', txt):
                    continue
                pg = etree.Element('cite')
                pg.text = txt.lstrip() + '.'
                elem.addprevious(pg)
            parent=elem.getparent()
            parent.remove(elem)

    for elem in root.iter(tag='cite'):
        if elem.text is not None and lang_check(elem.text) == 'en' and args.multilang:
            elem.set('lang', 'en')
        if elem.getnext() is not None and elem.getnext().tag != 'cite':
            elem.set('position', 'end')
        if elem.getprevious() is not None and elem.getprevious().tag != 'cite':
            elem.set('position', 'start')
    
    desc = {}
    desc['first_name'] = root.findtext("*//first-name")
    desc['last_name'] = root.findtext("*//last-name")
    desc['annotation'] = root.find("*//annotation")
    desc['book_title'] = root.findtext("*//book-title")
    desc['body'] = root.find("body")

    cover_img = root.find("*//coverpage/image")
    if cover_img is not None:
        img_link = cover_img.get('{http://www.w3.org/1999/xlink}href')[1:]
        for img_bin in root.iter(tag="binary"):
            if img_bin.get('id') == img_link:
                imgdata = base64.b64decode(img_bin.text)
                with open(args.work_dir + '/cover.jpg', 'wb') as f_cover:
                    f_cover.write(imgdata)
    else:
        add_text_cover( \
            f'{args.work_dir}/cover.jpg', \
            f"{desc['first_name']} {desc['last_name']}", \
            desc['book_title']
        )

    return desc


#etree.ElementTree(root).write('tmp/1.fb2', encoding='utf-8', pretty_print=True, xml_declaration=True)
