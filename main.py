#!/usr/bin/env python
import sys
<<<<<<< HEAD
from datetime import datetime

import whoosh.index as index
from colorama import init, Fore, Back, Style
from fuzzywuzzy import fuzz
from whoosh import fields, scoring
from whoosh.analysis import StandardAnalyzer
=======
import whoosh
from whoosh import scoring, query
>>>>>>> master
from whoosh.qparser import QueryParser, FuzzyTermPlugin
from whoosh.query import Query
from datetime import datetime

from colorama import Fore, Back, Style, init as colorama_init
from lookup_attributes import lookup_attributes, magia_search
from lookup_attributes.search import ix

colorama_init()

def cprint(msg, foreground="black", background="white"):
    fground = foreground.upper()
    bground = background.upper()
    style = getattr(Fore, fground) + getattr(Back, bground)
    print(style + msg + Style.RESET_ALL)

<<<<<<< HEAD

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
    schema = fields.Schema(text_value=fields.TEXT(stored=True,
                           analyzer=StandardAnalyzer(minsize=1)),
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
        n = 10
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


=======
>>>>>>> master
def main(query: ("Query", 'option', 'q'), arg_sentence=None, ):
    # test_data = SENTENCES
    # test_data = get_test_data(config.TEST_DATA_CSV)
    if arg_sentence:
        test_data = [(arg_sentence, [])]
    else:
        test_data = [
            ("Do you have something like the 2005 Zinfandel of Turley?".lower(), []),
            ("latour", ['chateau latour']),
            ("red chateu latour", ['red', 'chateau latour']),
            ("red", ['red']),
            ("i want red chateau lator", ['red', 'chateau latour']),
            ("cabernet sauvignon", ['cabernet sauvignon']),
            ("caubernet sauvignon", ['cabernet sauvignon']),
            ("cabernet savignon", ['cabernet sauvignon']),
            ("caubernet sauvignon", ['cabernet sauvignon']),
            ("how are yoou", []),
            ("chateu meru lator", ['chateau latour']),
            ("chateau lator", ['chateau latour']),
            ("blak opul", ['black opal']),
            ("want red caubernet sauvignon", ['red', 'cabernet sauvignon'])
        ]
    print()
    print()
    success = 0
    total = len(test_data)

    if query:
<<<<<<< HEAD
        with magia_search._searcher(weighting=scoring.BM25F()) as s:
=======
        with magia_search._searcher(weighting=  scoring.BM25F()) as s:
>>>>>>> master
            qp = QueryParser("text_value", schema=magia_search._schema)
            qp.add_plugin(FuzzyTermPlugin)
            q = qp.parse(query)
            magia_search.get_search_results(ix, "text_value", s, q)
            sys.exit()

    for sentence, expected in test_data:
        orig_sentence = sentence
        print("Input sentence: {}".format(sentence))
        start_time = datetime.now()
        result = []
        iteration = 0
        result = lookup_attributes(sentence)

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
