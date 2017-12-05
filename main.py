#!/usr/bin/env python
import os
import json
from datetime import datetime
import csv
import ast

import whoosh.index as index
from whoosh.qparser import QueryParser, OrGroup, FuzzyTermPlugin, AndMaybeGroup
from whoosh import query
from whoosh.query import Query, Term, Or, And, FuzzyTerm, Phrase
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


class MagiaSearch:
    def __init__(self, index):
        self._searcher = index.searcher
        self._schema = index.schema

    def perform_search(self, sentence):
        with self._searcher() as s:
            tokens = sentence.split()
            tokens = [token for token in tokens if token != REPLACED]
            f = 'text_value'
            exact_and_match = And([Term(f, token) for token in tokens], boost=4)
            exact_or_match = Or([Term(f, token) for token in tokens], boost=2, scale=0.9)
            fuzzy_or_match = Or([FuzzyTerm(f, token, prefixlength=2) for token in tokens if len(token) >= 4], boost=1, scale=0.9)
            #q = exact_and_match \
                # | exact_or_match \
                # | fuzzy_or_match
            q = exact_and_match | exact_or_match | fuzzy_or_match
            #q = exact_and_match
            print(q)
            search_result = s.search(q, terms=True, limit=10)
            values = [x['text_value'] for x in search_result]
            print('top records found:')
            top_ten = zip(search_result.items(), values)
            for item in top_ten:
                print('*  ', item[0][1], item[1])
            matched = [match[1].decode('utf-8') for x in search_result for match in x.matched_terms()]
            if values:
                return values[0], list(set(matched))
            else:
                return None, None

def main(arg_sentence=None):
    ix = get_index(config.INDEXDIR_PATH)  # get document index


    # test_data = SENTENCES
    #test_data = get_test_data(config.TEST_DATA_CSV)
    if arg_sentence:
        test_data = [(arg_sentence, [])]
    else:
        test_data = [
            ("latour", [])
            #("red latour", ['red', 'chateau latour']),
            #("red", ['red', 'chateau latour']),
            #("i want red chateau lator", ['red', 'chateau latour']),
            #("cabernet sauvignon", ['cabernet sauvignon']),
            #("caubernet sauvignon", ['cabernet sauvignon']),
            #("cabernet savignon", ['cabernet sauvignon']),
            #("caubernet sauvignon", ['cabernet sauvignon']),
            #("how are yoou", []),
            #("chateu meru lator", ['chateau latour']),
            #("chateau lator", ['chateau latour']),
            #("blak opul", ['black opal']),
           # ("want red caubernet sauvignon", ['cabernet sauvignon'])
        ]
    print()
    print()
    success = 0
    total = len(test_data)
    magia_search = MagiaSearch(ix)
    for sentence, expected in test_data:
        orig_sentence = sentence
        print("Input sentence: {}".format(sentence))
        start_time = datetime.now()
        result = []
        iteration = 0
        while True:
            iteration += 1

            item, terms = magia_search.perform_search(sentence)
            #exact = magia_search.perform_exact_search(sentence)
            #print('Exact:', exact)
            if not item or item in result:
                print('No more items')
                break
            result.append(item)
            print("Iteration #{}: {} ".format(iteration, result))
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
    import plac
    plac.call(main)
