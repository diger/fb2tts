import re
import pymorphy3
from libs.utils import get_args, num_dict

mrf = num_dict['mrf']
t_units = num_dict['t_units']
hundreds = num_dict['hundreds']
buildup = num_dict['buildup']
units_abbr = num_dict['units_abbr']

args =''
morph = pymorphy3.MorphAnalyzer()

# Updated mapping dictionary with common digraphs
cyrrilization_mapping_extended = {
    'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е',
    'f': 'ф', 'g': 'г', 'h': 'х', 'i': 'и', 'j': 'й',
    'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о',
    'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т',
    'u': 'у', 'v': 'в', 'w': 'в', 'x': 'кс', 'y': 'ы',
    'z': 'з',
    # Common digraphs
    'sh': 'ш', 'ch': 'ч', 'th': 'з', 'ph': 'ф', 'oo': 'у', 'ee': 'и', 'kh': 'х',
    # common trigraphs
    'sch': 'ск'
    # Capital letters are also converted to lowercase in the cyrrilization
}

# Month names in Russian in the genitive case
month_names = {
    '01': 'января', '02': 'февраля', '03': 'марта',
    '04': 'апреля', '05': 'мая', '06': 'июня',
    '07': 'июля', '08': 'августа', '09': 'сентября',
    '10': 'октября', '11': 'ноября', '12': 'декабря'
}

# Russian letter to its phonetic pronunciation mapping
pronunciation_map = {
    'А': 'а', 'Б': 'бэ', 'В': 'вэ', 'Г': 'гэ', 'Д': 'дэ',
    'Е': 'е', 'Ё': 'ё', 'Ж': 'жэ', 'З': 'зэ', 'И': 'и',
    'Й': 'ий', 'К': 'ка', 'Л': 'эл', 'М': 'эм', 'Н': 'эн',
    'О': 'о', 'П': 'пэ', 'Р': 'эр', 'С': 'эс', 'Т': 'тэ',
    'У': 'у', 'Ф': 'эф', 'Х': 'ха', 'Ц': 'цэ', 'Ч': 'чэ',
    'Ш': 'ша', 'Щ': 'ща', 'Ъ': 'твёрдый знак', 'Ы': 'ы', 'Ь': 'мягкий знак',
    'Э': 'э', 'Ю': 'ю', 'Я': 'я'
}

# Function to expand abbreviations in the text
def expand_abbreviations(text):
    # Regex to find sequences of uppercase Cyrillic letters
    abbreviations = re.findall(r'\b[А-ЯЁ]{2,}\b', text)

    # Expand each abbreviation using the pronunciation map
    for abbr in abbreviations:
        # Create a pronounced form of the abbreviation
        pronounced_form = ' '.join(pronunciation_map[letter] for letter in abbr if letter in pronunciation_map)
        # Replace the abbreviation with its pronounced form
        text = text.replace(abbr, pronounced_form)

    return text


def cyrrilize(text):
    """Convert a given text from Latin script to an approximate Cyrillic script in lowercase,
    taking into account common digraphs."""
    text = text.lower()  # Convert text to lowercase
    cyrrilized_text = ""
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i:i+2] in cyrrilization_mapping_extended:
            # If a digraph is found, add its cyrrilization and increment by 2
            cyrrilized_text += cyrrilization_mapping_extended[text[i:i+2]]
            i += 2
        else:
            # Add the cyrrilization of a single character
            cyrrilized_text += cyrrilization_mapping_extended.get(text[i], text[i])
            i += 1
    return cyrrilized_text

def normalize_number_with_text(text):
    num_pattern = re.compile(r'(\w+|\b|\W)[\s|\b](\d+[.,-]\d+|\d{2}\.\d{2}\.\d{4}|\d+\S\d+|\d+)([!-/:-@[-`{-~]\w{1,2}|[!-/:-@[-`{-~]\w{1,2}\s|\s|\b|\D)(\w{3,}|\W|$)', re.IGNORECASE)
    def normalize_num(match):
        result = [match.groups()]
        if result:
            for stor in result:
                stor = list(stor)
                if args.debug == 3: print(f'Анализ: {stor}')
                pre_attr = morph.parse(stor[0])
                data_attr = morph.parse(stor[3])[0]
                dattr = {}
                if stor[3] in units_abbr:
                    bks = morph.parse(units_abbr[stor[3]])[0]
                    stor[3] = bks.make_agree_with_number(int(stor[1][-1])).word
                if stor[0].lower() == 'к' and data_attr.tag.POS != 'NOUN':
                    dattr = {'POS': 'NOUN', 'case': 'loc2', 'gender': 'masc', 'number': 'sing'}
                dmy = re.match(r'(\d{2})\.(\d{2})\.(\d{4})', stor[1])
                nn = re.findall(r'(\d+)(\D+)(\d+)', stor[1])
                if dmy:
                    d_month = month_names[dmy.groups(0)[1]]
                    bks = morph.parse(d_month)[0]
                    d_year = num_to_words(pre_attr, int(dmy.groups(0)[2]), bks)
                    last_word = d_month + ' ' + d_year + stor[3]
#                    print(stor[0] + ' ' + num_to_words(pre_attr, int(dmy.groups(0)[0]), bks) + ' ' + last_word)
                    return stor[0] + ' ' + num_to_words(pre_attr, int(dmy.groups(0)[0]), bks) + ' ' + last_word
                if nn:
                    inter = ', '
                    dattr = {'POS': 'NOUN', 'case': 'loct', 'gender': 'femn', 'number': 'plur'}
                    if nn[0][1] == ',' or nn[0][1] == '.' or nn[0][1] == '-':
                        inter = ' и '
                        dattr = {'POS': 'NOUN', 'case': 'accs', 'gender': 'masc', 'number': 'sing'}
                    first_num = num_to_words(pre_attr, int(nn[0][0]), data_attr, dattr)
                    last_word = expand_abbr(stor[3],int(nn[0][2]),data_attr,pre_attr)
                    data_attr = morph.parse(last_word)[0]
                    second_num = num_to_words(pre_attr, int(nn[0][2]), data_attr, dattr)
#                    print(stor[0] + ' ' + first_num + inter + second_num + ' ' + last_word)
                    return stor[0] + ' ' + first_num + inter + second_num + ' ' + last_word
                if len(stor[2]) > 3:
                    last_word = re.sub(r'[!-/:-`{-~]', '', stor[2]) + stor[3]
                if stor[2] in buildup:
                    dattr = buildup[stor[2]]
                    if pre_attr[0].tag.POS == 'PREP' and buildup[stor[2]]['case'] == 'ablt':
                        dattr['case'] = 'loct'
                last_word = expand_abbr(stor[3],int(stor[1]),data_attr,pre_attr)

                if args.debug == 3:
                    print("Морф. анализ 1-го слова| " + str(pre_attr[0].tag) + " |")
                    print("Морф. анализ 3-го слова| " + str(data_attr.tag) + " |")

                if args.debug == 3: print(stor[0] + ' ' + num_to_words(pre_attr, int(stor[1]), data_attr, dattr) + ' ' + last_word)
                return stor[0] + ' ' + num_to_words(pre_attr, int(stor[1]), data_attr, dattr) + ' ' + last_word

    normalized_text = num_pattern.sub(normalize_num, text)
    return normalized_text

def normalize_number_without_text(text):
    num_pattern = re.compile(r'(\d+)', re.IGNORECASE)
    def normalize_num(match):
        result = [match.groups()]
        if result:
            for stor in result:
                stor = list(stor)
                dattr = {'POS': 'NOUN', 'case': 'accs', 'gender': 'femn', 'number': 'sing'}
                if args.debug == 3: print(num_to_words(None, int(stor[0]), None, dattr) + ' ' + stor[0])
                return num_to_words(None, int(stor[0]), None, dattr)

    normalized_text = num_pattern.sub(normalize_num, text)
    return normalized_text

def expand_abbr(match, cnum, data_attr, pre_attr):
    if 'Abbr' in data_attr.tag and match in units_abbr:
#        print(data_attr)
        bks = morph.parse(units_abbr[match])[0]
#       if pre_attr[0].tag.POS == 'ADVB':
#            print(bks.inflect({'gent'}))
#            return bks.make_agree_with_number(cnum%10).word
        return bks.make_agree_with_number(cnum%10).word
    else:
        return match

def num_to_words(attr1, n, attr2, adv_attr=None):

    if adv_attr:
        pos0 = adv_attr['POS']
        pos = adv_attr['POS']
        case = adv_attr['case']
        gender = adv_attr['gender']
        ch_num = adv_attr['number']
    else:
        pos = attr2.tag.POS
        pos0 = attr1[0].tag.POS
        case = attr2.tag.case
        gender = attr2.tag.gender
        ch_num = attr2.tag.number
    
        if pos == 'NOUN':
            if case == 'accs' and gender == 'masc' and ch_num == 'sing' and \
                (pos0 == 'VERB' or pos0 == 'CONJ' or pos0 == 'PREP'):
                case = 'nomn'
            if case == 'gent' and gender == 'masc' and ch_num == 'sing' and pos0 == 'VERB':
                ch_num = 'plur'
            if case == 'nomn' and gender == 'masc' and ch_num == 'sing' and \
                (pos0 == 'ADVB' or pos0 == 'PREP'):
                ch_num = 'plur'
                gender = 'femn'
            if (case == 'loc2' or case == 'datv'):
                case = 'loct'

        elif pos == 'ADJF' or pos == 'NPRO':
            if case == 'loct' or (case == 'datv' and pos0 == 'PREP'):
                case = 'gent'
            if case == 'nomn':
                case = 'gent'
                gender ='femn'
                ch_num = 'plur'
            if (case == 'ablt' or case == 'datv') and pos0 == 'NOUN':
                case = attr1[0].tag.case
                gender = attr1[0].tag.gender
                ch_num = attr1[0].tag.number
        elif pos == 'PRTF':
                gender = 'femn'
        elif not pos:
            if pos0 == 'ADVB':
                case = 'gent'
                gender = 'masc'
                ch_num = 'plur'
            elif pos0 == 'CONJ' or pos0 == 'PREP':
                case = 'accs'
                gender = 'masc'
                ch_num = 'sing'
            elif pos0 == 'ADJF':
                case = 'loct'
                if not gender: gender = 'femn'
                if not ch_num: ch_num = 'plur'
            elif pos0 == 'NPRO':
                case = 'accs'
            elif attr1[0].tag.case:
                case = attr1[0].tag.case
                if case == 'ablt': case = 'accs'
                gender = attr1[0].tag.gender
                ch_num = attr1[0].tag.number
            else:
                case = 'accs'
                gender = 'masc'
                ch_num = 'sing'

    if not case: case = 'accs'
    if not ch_num: ch_num = 'sing'
    if not gender: gender = 'femn'

    if args.debug == 3:
        print(case)
        print(gender)
        print(ch_num)

    """
    Convert a number into its word components in Russian
    """
    if n == 0:
        return 'ноль'

    teens = ['десят','одиннадцат','двенадцат','тринадцат','четырнадцат','пятнадцат','шестнадцат','семнадцат','восемнадцат','девятнадцат']
    tens = ['','десят','двадцат','тридцат','сороков','пятьдесят','шестьдесят','семьдесят','восемьдесят','девяност']    
    million_units = morph.parse('миллион')[0]
    billion_units = morph.parse('миллиард')[0]
    thousand_units = morph.parse('тысяча')[0]

    words = []

    # Helper function to handle numbers below 1000
    def under_thousand(number):
        if number == 0:
            return []
        elif number < 10:
           return [t_units[case][gender][ch_num][number]]
        elif number < 20:
            if case == 'accs':
                return [teens[number - 10] + mrf['nomn']['masc']['teens']['plur']]
            else:
                return [teens[number - 10] + mrf[case][gender]['teens'][ch_num]]
        elif number < 100 and number % 10 != 0:
            if number % 100 // 10 * 10 == 40:
                return ['сорок', t_units[case][gender][ch_num][number % 10]]
            else:
                if number // 10 == 2:
                    cif = 'двадцать'
                    if case == 'ablt':
                        cif = 'двадцати'
                    return [cif, t_units[case][gender][ch_num][number % 10]]
                if number // 10 == 3:
                    cif = 'тридцать'
                    if case == 'ablt':
                        cif = 'тридцати'
                    return [cif, t_units[case][gender][ch_num][number % 10]]
                if number // 10 == 9:
                    return ['девяносто', t_units[case][gender][ch_num][number % 10]]
                elif case == 'loct' or case == 'loc2' or (case == 'gent' and ch_num != 'plur'):
                    return [tens[number // 10] + mrf['gent']['femn']['tens']['sing'], t_units[case][gender][ch_num][number % 10]]
                elif case == 'accs':
                    return [tens[number // 10] + mrf['gent']['masc']['tens']['plur'], t_units[case][gender][ch_num][number % 10]]
                elif case == 'nomn':
                    return [tens[number // 10] + mrf['gent']['neut']['tens']['sing'], t_units[case][gender][ch_num][number % 10]]
                else:
                    return [tens[number // 10] + mrf[case][gender]['tens'][ch_num], t_units[case][gender][ch_num][number % 10]]
        elif number < 100:
            if number // 10 == 2 and ch_num == 'plur':
                return ['двадцать']
            if number // 10 == 3 and ch_num == 'plur':
                    return ['тридцать']
            if number // 10 == 4 and case == 'gent':
                if pos0 == 'ADVB':
                    return ['сорока']
                else:
                    return ['сороков' + mrf[case][gender]['tens'][ch_num]]
            if number // 10 == 9:
                return ['девяносто']
            #elif (case == 'accs' or case == 'loct' or case == 'loc2' and ch_num == 'sing' and gender != 'femn') \
            elif (case == 'loct' or case == 'loc2' and ch_num == 'sing' and gender != 'femn') \
                or (case == 'gent' and ch_num == 'plur'):
                return [tens[number // 10] + mrf['gent']['femn']['tens']['sing']]
            else:
                return [tens[number // 10] + mrf[case][gender]['tens'][ch_num]]
        else:
            if case == 'accs' or case == 'nomn':
                return [hundreds['accs'][number // 100]] + under_thousand(number % 100)
            else:
                return [hundreds['gent'][number // 100]] + under_thousand(number % 100)

    # Break the number into the billions, millions, thousands, and the rest
    billions = n // 1_000_000_000
    millions = (n % 1_000_000_000) // 1_000_000
    thousands = (n % 1_000_000) // 1_000
    remainder = n % 1_000

    last = under_thousand(remainder)
    if billions:
        words += under_thousand(billions) + [billion_units.make_agree_with_number(billions).word]
    if millions:
        words += under_thousand(millions) + [million_units.make_agree_with_number(millions).word]
    if thousands:
        if thousands <= 9 and remainder == 0:
            words.append(t_units['loct']['masc']['plur'][thousands])
            words.append('тысячн' + mrf[case][gender]['teens'][ch_num])
        else:
            # Special case for 'one' and 'two' in thousands
            if thousands % 10 == 1 and thousands % 100 != 11:
                words.append('одна')
            elif thousands % 10 == 2 and thousands % 100 != 12:
                words.append('две')
            else:
                ch_num = 'plur'
                words += under_thousand(thousands)
               # words.append(t_units[case][gender]['plur'][thousands])
            words.append(thousand_units.make_agree_with_number(thousands).word)
    words += last

    last_num = ' '.join(word for word in words if word)
    last_num = last_num.split()[-1]

    return ' '.join(word for word in words if word)

def normalize_russian(text):
    global args
    args = get_args()
    #text = expand_unit_abbr(text)
    text = normalize_number_with_text(text)
    text = normalize_number_without_text(text)
    text = cyrrilize(text)
    return text
