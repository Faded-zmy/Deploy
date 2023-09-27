import re

def reformat_output(output, urls, cite=True):
    """
    :param output: llm direct output
    :param urls: all urls
    :return: formatted text, with urls, start from 1
    """

    # to solve the problem of referring to the same source with different superscripts
    # such as [1, 2, 3, 4] but 2,3,4 are the same source, change to [1, 2, 2, 2]

    replace_symbols = ['Ⅰ', 'II', "III", "IV", "V"]
    for i, url in enumerate(urls):
        output = output.replace(f'[{i+1}]', f'[{urls.index(url)+1}]')
    
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, output)
    citation_matches = [int(match) for match in matches] 
    citation_list= []
    for i in citation_matches:
        if i not in citation_list:
            citation_list.append(i)
    
    # to solve uncontinuous citing problem, such as [1, 1, 2, 5] -> [1, 1, 2, 3]
    for idx, citation in enumerate(citation_list):
        output = output.replace(f'[{citation}]', f'[{replace_symbols[idx]}]')
    for idx, symbol in enumerate(replace_symbols):
        output = output.replace(f'[{symbol}]', f'[{idx+1}]')

    # to solve conitinuous citing the same superscript
    def merge_consecutive_duplicate_references(text):
        references = []
        references_idx = []
        i = 0
        while i < len(text):
            if text[i] == '[':
                left_idx, right_idx = i, i
                for j in range(i+1, len(text)):
                    if not text[j].isdigit() and text[j] not in ['[', ']']:
                        right_idx = j
                        break
                references.append(text[left_idx: right_idx])
                references_idx.append([left_idx, right_idx])
                i = j
                continue
            i += 1
        for i in range(len(references)-1, 0, -1):
            if references[i] == references[i-1]:
                left_index, rigth_index = references_idx[i-1][0], references_idx[i-1][1]
                fill_string = re.sub(r'\d', 'x', text[left_index:rigth_index])
                text = text[0:left_index] + fill_string + text[rigth_index:]
        output = text.replace('[x]', '').replace(' .', '.')
        return output
    
    # to sovle the problem of reverse citing, such as [2][1] -> [1][2]
    def resort_references(text):
        references = []
        references_idx = []
        i = 0
        while i < len(text):
            if text[i] == '[':
                left_idx, right_idx = i, i
                for j in range(i+1, len(text)):
                    if not text[j].isdigit() and text[j] not in ['[', ']']:
                        right_idx = j
                        break
                references.append(text[left_idx: right_idx])
                references_idx.append([left_idx, right_idx])
                i = j
                continue
            i += 1
        for ref in references:
            ref_matches = re.findall(pattern, ref)
            ref_cite = [int(match) for match in ref_matches] # 匹配
            ref_cite.sort()
            resort_ref = ''.join([f'[{n}]' for n in ref_cite])
            if resort_ref != ref:
                text = text.replace(ref, resort_ref)
        return text
    
    output = merge_consecutive_duplicate_references(output)
    output = resort_references(output)
    if cite:
        output += "\n" + "".join([f"[{i + 1}]" for i in range(len(citation_list))]) + " are given by following links:"
    return output, citation_list