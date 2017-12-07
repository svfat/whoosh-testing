#!/usr/bin/env python
import sys
import whoosh
from whoosh import scoring, query
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
        with magia_search._searcher(weighting=  scoring.TF_IDF()) as s:
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
