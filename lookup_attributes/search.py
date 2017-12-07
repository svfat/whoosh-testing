import ast
import csv
import os
import re

import whoosh.index as index

from fuzzywuzzy import fuzz
from whoosh import fields
from whoosh.analysis import StandardAnalyzer
from whoosh.query import Term, Or, And, FuzzyTerm

import config
from lookup_attributes.search_result import SearchResult
from lookup_attributes.stopwords import STOPWORDS

REPLACED = '------'

SCHEMA = fields.Schema(text_value=fields.TEXT(stored=True,
                                              analyzer=StandardAnalyzer(minsize=1, stoplist=STOPWORDS)),
                       text_value_ngram=fields.NGRAMWORDS(stored=True),
                       attribute_code=fields.STORED,
                       node_id=fields.STORED)


def fast_replace_single_token(token, stub, orig_str):
    return re.sub(r"\b{}\b".format(token), stub, orig_str)


def fuzzy_replace(str_a, stub, orig_str):
    """
    search for exact dictionary term in query.
    If not found, search for fuzzy term with distance < X (or some factor if using fuzzywuzzy).

    TODO:
    If not found, search for each exact individual terms from query results. If any remaining,
    search for fuzzywuzzy individual terms from query results
    """

    RATIO = 74

    l = len(str_a.split())  # Length to read orig_str chunk by chunk
    splitted = [t for t in orig_str.split() if t != stub]
    if l == 1 and str_a in orig_str:
        # only one word there
        return fast_replace_single_token(str_a, stub, orig_str)

    for i in range(len(splitted) - l + 1):
        test = " ".join(splitted[i:i + l])
        if fuzz.ratio(str_a, test) > RATIO:  # Using fuzzwuzzy library to test ratio
            before = " ".join(splitted[:i])
            after = " ".join(splitted[i + 1:])
            return before + " " + stub + " " + after
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
    schema = SCHEMA
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
                                    attribute_code=row['attribute_code'],)
                                    #node_id=row['node_id']) # TODO add node_id to source table
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
        self._index = index
        self._searcher = index.searcher
        self._schema = index.schema

    def perform_search(self, sentence):
        with self._searcher() as s:
            tokens = sentence.split()
            tokens = [token for token in tokens if token != REPLACED]
            f = 'text_value'
            exact_and_match = And([Term(f, token) for token in tokens], boost=.45)
            exact_or_match = Or([Term(f, token) for token in tokens], boost=.45, scale=0.9)
            fuzzy_or_match = Or([FuzzyTerm(f, token, prefixlength=2) for token in tokens if len(token) >= 4], boost=.1,
                                scale=0.9)
            # q = exact_and_match \
            # | exact_or_match \
            # | fuzzy_or_match
            q = exact_and_match | exact_or_match | fuzzy_or_match

            my_match = Or([Term(f, token) for token in tokens], boost=1)

            # my_fuzzy_or_match = Or([FuzzyTerm(f, token, prefixlength=2) for token in tokens if len(token) >= 3], boost=1.0,
            #                    scale=0.9)
            # q = my_match


            # q = exact_and_match
            print(q)
            search_results = self.get_search_results(self._index, f, s, q)

            for x in search_results:
                print(x, x.score)

            if search_results:
                score, text, matched = search_results[0].items()
                return text, list(set(matched))
            else:
                return None, None

    def get_search_results(self, ix, field_name, searcher, query):
        n = 16
        search_results = searcher.search(query, terms=True, limit=n)
        print('top records found:')
        top_n = list(zip(search_results.items(), [(hit[field_name], hit.matched_terms()) for hit in search_results]))
        result = []
        for doc_score, hit in top_n:
            result.append(SearchResult(initial_score=doc_score[1],
                                       text=hit[0],
                                       ix=ix,
                                       field_name=field_name,
                                       matched=[x[1] for x in hit[1]]))
        result = list(sorted(result, key=lambda x: x.score, reverse=True))

        return result


ix = get_index(config.INDEXDIR_PATH)  # get document index
magia_search = MagiaSearch(ix)


def lookup_attributes(sentence):
    attributes = []
    i = 0
    while sentence:
        i += 1
        attr, terms = magia_search.perform_search(sentence)
        if not attr or attr in attributes:
            print('No more attributes')
            break
        attributes.append(attr)
        print("Current iteration result: {} ".format(attributes))
        for word in terms:
            # sentence = sentence.replace(word, '-------')
            sentence = fuzzy_replace(word, REPLACED, sentence)
        print("Tokens left: {}".format(sentence))

    if len(attributes) > 1:
        final_result = []
        for token1 in attributes:
            second_list = [t for t in attributes if t != token1]
            for token2 in second_list:
                if token1 in token2:
                    continue
                else:
                    final_result.append(token1)
        attributes = final_result
    return list(set(attributes))
