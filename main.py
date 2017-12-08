#!/usr/bin/env python
import sys
from datetime import datetime

from colorama import Fore, Back, Style, init as colorama_init
from whoosh import scoring
from whoosh.qparser import QueryParser, FuzzyTermPlugin
from whoosh.query import Query

from lookup_attributes import lookup_attributes, magia_search
from lookup_attributes.field_names import TEXT_FIELD
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
            # ("Do you have something like the 2005 Zinfandel of Turley?".lower(), []),
            ("redd wine nappa chateau latoor", []),
            ("nappa valley", ['napa valley']),
            ("latour", ['chateau latour']),
            ("red chateu latour", ['red', 'chateau latour']),
            ("red", ['red']),
            ("red chateau lator", ['red', 'chateau latour']),
            ("cabernet sauvignon", ['cabernet sauvignon']),
            ("caubernet sauvignon", ['cabernet sauvignon']),
            ("cabernet savignon", ['cabernet sauvignon']),
            ("caubernet sauvignon", ['cabernet sauvignon']),
            ("how are yoou", []),
            ("chateu meru lator", ['merus', 'chateau latour']),
            ("chateau lator", ['chateau latour']),
            ("blak opul", ['black opal']),
            ("red caubernet sauvignon", ['red', 'cabernet sauvignon'])
        ]
    print()
    print()
    success = 0
    total = len(test_data)

    if query:
        with magia_search._searcher(weighting=scoring.TF_IDF()) as s:
            qp = QueryParser(TEXT_FIELD, schema=magia_search._schema)
            qp.add_plugin(FuzzyTermPlugin)
            q = qp.parse(query)
            magia_search.get_search_results(ix, s, q)
            sys.exit()

    failed = []
    for chunk, expected in test_data:
        orig_chunk = chunk
        print("Input chunk: {}".format(chunk))
        start_time = datetime.now()
        result = lookup_attributes(chunk)

        if sorted(result) == sorted(expected):
            success += 1
            cprint('Success', foreground="green", background="black")
        else:
            cprint('Fail', foreground="red", background="black")
            failed.append((chunk, result, expected))

        print('Completed in {}'.format(datetime.now() - start_time))
        print('Expected', expected)
        print('Got:', result)
        print('--------------')
        print()
    print("{}/{} tests passed. {}%".format(success, total, success * 100 // total))
    if failed:
        print()
        cprint('Failed', foreground="red", background="black")
        for chunk, result, expected in failed:
            print('*IN: {} *OUT: {} *EXPECTED: {}'.format(chunk, result, expected))

if __name__ == "__main__":
    import plac

    plac.call(main)
