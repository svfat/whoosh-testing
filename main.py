#!/usr/bin/env python
import os
import json
from datetime import datetime
import csv
import ast

import whoosh.index as index
from whoosh.qparser import QueryParser, OrGroup, FuzzyTermPlugin, AndMaybeGroup
from whoosh import query
from whoosh import fields
from whoosh import scoring
from whoosh.analysis import StemmingAnalyzer

import config
from data import SENTENCES

from fuzzywuzzy import fuzz

from colorama import init, Fore, Back, Style

init()

REPLACED = '------'


def cprint(msg, foreground="black", background="white"):
    fground = foreground.upper()
    bground = background.upper()
    style = getattr(Fore, fground) + getattr(Back, bground)
    print(style + msg + Style.RESET_ALL)


def fuzzy_replace(str_a, str_b, orig_str):
    l = len(str_a.split())  # Length to read orig_str chunk by chunk
    splitted = orig_str.split()
    for i in range(len(splitted) - l + 1):
        test = " ".join(splitted[i:i + l])
        if fuzz.ratio(str_a, test) > 75:  # Using fuzzwuzzy library to test ratio
            before = " ".join(splitted[:i])
            after = " ".join(splitted[i + 1:])
            return before + " " + str_b + " " + after
    return orig_str


def create_dir(directory):
    """
    Create directory if not exists
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def create_index(directory):
    """
    Generate Whoosh index from text file
    """
    print('Generating index in {}'.format(directory))
    # schema = Schema(text_value=TEXT(stored=True), attribute_code=TEXT(stored=True))
    schema = fields.Schema(text_value=fields.TEXT(stored=True),
                           text_value_ngram=fields.NGRAMWORDS(stored=True),
                           attribute_code=fields.TEXT(stored=True))
    create_dir(directory)
    ix = index.create_in(directory, schema)
    writer = ix.writer()
    total = 0
    with open('domain_dictionary.csv', 'r') as f:
        rdr = csv.DictReader(f)
        for i, row in enumerate(rdr):
            if not i % 10000:
                print(i)
            text_value = row['text_value'].lower().strip()
            if text_value:
                writer.add_document(text_value=text_value,
                                    text_value_ngram=text_value,
                                    attribute_code=row['attribute_code'])
                total += 1
    print('Writing {} records...'.format(total))
    writer.commit()
    print("{} elements indexed".format(total))
    return ix


def get_index(directory):
    """
    Return Whoosh index
    """
    try:
        ix = index.open_dir(directory)
    except:
        ix = create_index(directory)
        ix = index.open_dir(directory)
    return ix


def extract_expected(data):
    slot = ast.literal_eval(data)
    response = slot.get('response', {})
    expected = []
    if 'entity' in response:
        attrs1 = response['entity']['attributes']
        expected = [a.get('value') for a in attrs1]
    return expected


def get_test_data(csv_file):
    result = []
    with open(csv_file, 'r') as f:
        rdr = csv.DictReader(f)
        for i, row in enumerate(rdr):
            sentence = row['Sentence']
            try:
                expected = extract_expected(row['Expected Slot'])
            except:
                print("Can't evaluate expected value for line #{} - '{}'".format(i, sentence))
            else:
                result.append((sentence, expected))
    return result


def prepare_input_sentence(sentence):
    sentence = sentence.strip().lower()
    stopwords = ['wines']
    for word in stopwords:
        sentence = sentence.replace(word)
    return sentence


def find_ngrams(l: list, n: int):
    return list(zip(*[l[i:] for i in range(n)]))


def perform_search(searcher, schema, sentence):
    result = []
    # first
    from whoosh.query import FuzzyTerm
    class MyFuzzyTerm(FuzzyTerm):
        def __init__(self, fieldname, text, boost=1.0, maxdist=2, prefixlength=1, constantscore=True):
            super().__init__(fieldname, text, boost, maxdist, prefixlength, constantscore)

    qp = QueryParser('text_value', schema=schema, group=OrGroup.factory(0.9), termclass=FuzzyTerm)
    qp.add_plugin(FuzzyTermPlugin())
    tokens = sentence.split()
    ngrams = find_ngrams(tokens, 1)
    chunks = [' '.join(x) for x in ngrams]
    search_query = ' OR '.join(chunks) + ' OR (' + ' AND '.join(chunks) + ')'
    q = qp.parse(search_query)
    search_result = searcher.search(q, terms=True, limit=1)
    values = [x['text_value'] for x in search_result]
    matched = [match[1].decode('utf-8') for x in search_result for match in x.matched_terms()]
    if values:
        return values[0], list(set(matched))
    else:
        return None, None


def main():
    ix = get_index(config.INDEXDIR_PATH)  # get document index

    # creating QueryParser
    qp = QueryParser("text_value", schema=ix.schema, group=OrGroup.factory(1))
    # we will use FuzzyTermPlugin if nothing was found with exact search
    qp.add_plugin(FuzzyTermPlugin())

    # test_data = SENTENCES
    #test_data = get_test_data(config.TEST_DATA_CSV)
    test_data = [
        ("cabernet sauvignon", ['cabernet sauvignon']),
        ("caubernet sauvignon", ['cabernet sauvignon']),
        ("cabernet savignon", ['cabernet sauvignon']),
        ("caubernet sauvignon", ['cabernet sauvignon']),
        ("how are yoou", []),
        ("chateu meru lator", ['chateau latour']),
        ("chateau lator", ['chateau latour']),
        ("blak opul", ['black opal'])
    ]
    print()
    print()
    success = 0
    total = len(test_data)
    for sentence, expected in test_data:
        orig_sentence = sentence
        print("Input sentence: {}".format(sentence))
        start_time = datetime.now()
        with ix.searcher(weighting=scoring.PL2()) as s:
            result = []
            iteration = 0
            while True:
                iteration += 1
                print("Iteration #{} ".format(iteration), end='')
                item, terms = perform_search(s, ix.schema, sentence.lower())
                if not item or item in result:
                    print('No more items')
                    break
                result.append(item)
                print(result)
                for word in terms:
                    # sentence = sentence.replace(word, '-------')
                    sentence = fuzzy_replace(word, REPLACED, sentence)
                print("Tokens left: {}".format(sentence))

        if len(result) > 1:
            final_result = []
            for token1 in result:
                second_list = [t for t in result if t != token1]
                for token2 in second_list:
                    if token1 in token2:
                        continue
                    else:
                        final_result.append(token1)
            result = final_result

        if sorted(result) == sorted(expected):
            success += 1
            cprint('Success', foreground="green", background="black")
        else:
            cprint('Fail', foreground="red", background="black")

        print('Completed in {}'.format(datetime.now() - start_time))
        print('Expected', expected)
        print('Got:', result)
        print('--------------')
        print()
    print("{}/{} tests passed. {}%".format(success, total, success * 100 // total))


if __name__ == "__main__":
    main()
