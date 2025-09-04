import re

from libs.russian import normalize_russian
from libs.utils import accentizer, word_dict, get_args, device

accentizer.load(omograph_model_size='big_poetry', use_dictionary=True, device=device, workdir="./model")

args = get_args()
cust_dict = word_dict['cust_dict']
exc_abrs = word_dict['exc_abrs']
list_of_snd = word_dict['list_of_snd']

alphabet_map = {
    "А": "А",
    "Б": "Бэ",
    "В": "Вэ",
    "Г": "Гэ",
    "Д": "Дэ",
    "Е": "Е",
    "Ё": "Ё",
    "Ж": "Жэ",
    "З": "Зэ",
    "И": "И",
    "К": "Ка",
    "Л": "Лэ",
    "М": "эМ",
    "Н": "эН",
    "О": "О",
    "П": "Пэ",
    "Р": "эР",
    "С": "эС",
    "Т": "Тэ",
    "У": "У",
    "Ф": "эФ",
    "Х": "Хэ",
    "Ц": "Цэ",
    "Ч": "Чэ",
    "Ш": "Шэ",
    "Щ": "Ща",
    "Я": "Я"
}

punctuation = r'[\s,.?!/)\'\]>]'

def preprocess(string):
    string = re.sub(r'°', 'градус', string)
    string = re.sub( '№|#', 'номер ', string)
    string = re.sub( '\+', 'плюс', string)
    string = replace_abbreviations(string)
    string = profanity(string)
    string = replace_roman(string)
    string = len_check(string)
    string = replace_hrname(string)
    string = normalize_russian(string)
    string = garbage(string)
    string = accentizer.process_all(string,'\+\w+|\w+\+\w+')
    string = re.sub('(\w)\s-\s(\w)', r'\1-\2', string)

    return string

def replace_abbreviations(string):
    except_abr =  '|'.join(x[0] for x in exc_abrs)
    str_list = string.split()
    ar2str = []
    for str in str_list:
        pattern = re.compile(r'\b[А-Я]{2,5}\b')
        if pattern.search(str) and not re.findall(rf'\b({except_abr})\b', str):
            str = replace_abbreviation(str)
        elif re.findall(rf'\b({except_abr})\b', str):
            str =  str.lower()
        ar2str.append(str)
    ar_str = ' '
    string = ar_str.join(ar2str)

    return string

def replace_abbreviation(string):
    result = ""
    for char in string:
        result += match_mapping(char)

    return result

def match_mapping(char):
    for mapping in alphabet_map.keys():
        if char == mapping:
            return alphabet_map[char]

    return char

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

def len_check(string):
    out = []
    for word in string.split():
        out.append(word[:35])

    return ' '.join(out)

def profanity(string):
    string = re.sub( 'б\*\*\*', 'бляди', string)
    string = re.sub( 'б\*\*', 'бля', string)
    string = re.sub( 'с\*\*\*', 'с+ука', string)
    string = re.sub( 'по\*\*\*', 'п+охуй', string)
    string = re.sub( 'п\*\*\*\*', 'пизд+ец', string)
    string = re.sub( 'е\*\*\*', 'ебёт', string)

    return string

def garbage(string):
    string = re.sub('http[s]?://\S+', '', string)
    string = re.sub(r'(\’|«|»|”|„|\[|\*|\u201F|\u201C|\u2800|\(с\))', '', string)
    string = re.sub(r'(!\s|:\s|;\s|\s—|\s–|\s-|\?\s)', ', ', string)
    string = re.sub(',,', ', ', string)
    string = re.sub(r'(…|\.{3})|!|:|;|—|–|-|\?|\xa0', ' ', string)
    string = re.sub(r'(\)|\()|\]', '. ', string)
    string = re.sub(r'(\d+)(%)', r'\1 \2', string)
    string = re.sub(r'(\-)(\w{4,})', r' \2', string)

    return string

def replace_roman(string):
    # find a string of roman numerals.
    # Only 2 or more, to avoid capturing I and single character abbreviations, like names
    pattern = re.compile(rf'\s[IVXLCDM]{{2,}}{punctuation}')
    result = string
    while True:
        match = pattern.search(result)
        if match is None:
            break

        start = match.start()
        end = match.end()
        result = result[0:start + 1] + str(roman_to_int(result[start + 1:end - 1])) + result[end - 1:len(result)]

    return result

def replace_hrname(string):
    string_com = re.compile('|'.join(cust_dict.keys()))
    def r_name(found):
        return cust_dict[found.group(0)]

    string = string_com.sub(r_name, string)
    return string

def roman_to_int(s):
    rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    int_val = 0
    for i in range(len(s)):
        if i > 0 and rom_val[s[i]] > rom_val[s[i - 1]]:
            int_val += rom_val[s[i]] - 2 * rom_val[s[i - 1]]
        else:
            int_val += rom_val[s[i]]
    return int_val


def __main__(args):
    print(preprocess(args[1]))


if __name__ == "__main__":
    import sys
    __main__(sys.argv)
