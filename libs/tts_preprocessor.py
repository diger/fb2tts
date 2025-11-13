import re

from libs.russian import normalize_russian
from libs.utils import accentizer, word_dict, get_args

cust_dict = word_dict['cust_dict']
exc_abrs = word_dict['exc_abrs']

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

class TextParse:
    def __init__(self, accent, single_vowel=None):
        self.accent = accent
        self.single_vowel = single_vowel

    def preprocess(self, string):
        string = re.sub(r'°', 'градус', string)
        string = re.sub( '№|#', 'номер ', string)
        string = re.sub( '\+', 'плюс', string)
        string = self.replace_abbreviations(string)
        string = self.profanity(string)
        string = self.replace_roman(string)
        string = self.len_check(string)
        string = self.replace_hrname(string)
        string = normalize_russian(string)
        string = self.garbage(string)
        if self.accent:
            string = accentizer.process_all(string,'\+\w+|\w+\+\w+')
        string = re.sub('(\w)\s-\s(\w)', r'\1-\2', string)
        if self.single_vowel:
            string = self.rm_pl_single_vowel(string)

        return string

    def replace_abbreviations(self, string):
        except_abr =  '|'.join(x[0] for x in exc_abrs)
        str_list = string.split()
        ar2str = []
        for str in str_list:
            pattern = re.compile(r'\b[А-Я]{2,5}\b')
            if pattern.search(str) and not re.findall(rf'\b({except_abr})\b', str):
                str = self.replace_abbreviation(str)
            elif re.findall(rf'\b({except_abr})\b', str):
                str =  str.lower()
            ar2str.append(str)
        ar_str = ' '
        string = ar_str.join(ar2str)

        return string

    def replace_abbreviation(self, string):
        result = ""
        for char in string:
            result += self.match_mapping(char)

        return result

    def match_mapping(self, char):
        for mapping in alphabet_map.keys():
            if char == mapping:
                return alphabet_map[char]

        return char

    def len_check(self, string):
        out = []
        for word in string.split():
            out.append(word[:35])

        return ' '.join(out)

    def profanity(self, string):
        string = re.sub( 'б\*\*\*', 'бляди', string)
        string = re.sub( 'б\*\*', 'бля', string)
        string = re.sub( 'с\*\*\*', 'с+ука', string)
        string = re.sub( 'по\*\*\*', 'п+охуй', string)
        string = re.sub( 'п\*\*\*\*', 'пизд+ец', string)
        string = re.sub( 'е\*\*\*', 'ебёт', string)

        return string

    def garbage(self, string):
        string = re.sub('http[s]?://\S+', '', string)
        string = re.sub(r'(\’|«|»|”|„|\[|\*|\u201F|\u201C|\u2800|\(с\))', '', string)
        string = re.sub(r'(!\s|:\s|;\s|\s—|\s–|\s-|\?\s)', ', ', string)
        string = re.sub(',,', ', ', string)
        string = re.sub(r'(…|\.{3})|!|:|;|—|–|-|\?|\xa0', ' ', string)
        string = re.sub(r'(\)|\()|\]', '. ', string)
        string = re.sub(r'(\d+)(%)', r'\1 \2', string)
        string = re.sub(r'(\-)(\w{4,})', r' \2', string)

        return string

    def replace_roman(self, string):
        pattern = re.compile(rf'\s[IVXLCDM]{{2,}}{punctuation}')
        result = string
        while True:
            match = pattern.search(result)
            if match is None:
                break

            start = match.start()
            end = match.end()
            result = result[0:start + 1] + str(self.roman_to_int(result[start + 1:end - 1])) + result[end - 1:len(result)]

        return result

    def replace_hrname(self, string):
        string_com = re.compile('|'.join(cust_dict.keys()))
        def r_name(found):
            return cust_dict[found.group(0)]

        string = string_com.sub(r_name, string)
        return string

    def roman_to_int(self, s):
        rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        int_val = 0
        for i in range(len(s)):
            if i > 0 and rom_val[s[i]] > rom_val[s[i - 1]]:
                int_val += rom_val[s[i]] - 2 * rom_val[s[i - 1]]
            else:
                int_val += rom_val[s[i]]
        return int_val

    def rm_pl_single_vowel(self, text):
        def process_word(match):
            word = match.group()
            
            # Проверяем, есть ли в слове плюс перед гласной
            if '+' in word:
                # Находим все гласные в слове
                vowels = re.findall(r'[аеёиоуыэюя]', word, flags=re.IGNORECASE)
                
                # Если гласная только одна И есть плюс перед гласной
                if len(vowels) == 1:
                    # Удаляем все плюсы из слова
                    return word.replace('+', '')
            
            return word
        
        # Ищем все слова (включая те, что содержат +)
        return re.sub(r'[\+а-яё]+\b', process_word, text, flags=re.IGNORECASE)