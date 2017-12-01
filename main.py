#!/usr/bin/env python
import os

import whoosh.index as index
from whoosh.qparser import QueryParser, OrGroup, FuzzyTermPlugin
from whoosh.fields import *
from whoosh import scoring

import config
from data import SENTENCES



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
    schema = Schema(body=TEXT(stored=True))
    create_dir(directory)
    ix = index.create_in(directory, schema)
    writer = ix.writer()
    with open('magia_dictionary_en.txt', 'r') as f:
        for line in f:
            writer.add_document(body=line.strip())
    writer.commit()
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

def main():
    ix = get_index(config.INDEXDIR_PATH) # get document index

    # creating QueryParser
    qp = QueryParser("body", schema=ix.schema, group=OrGroup.factory(0.9))
    # we will use FuzzyTermPlugin if nothing was found with exact search
    qp.add_plugin(FuzzyTermPlugin())

    for sentence in SENTENCES:
        q = qp.parse(sentence)
        results = None
        with ix.searcher() as s:
            if config.CORRECTOR:
                # experiment with internal whoosh corrector
                # set CORRECTOR=True in config.py to use
                # I've got weird results, though
                corrected = s.correct_query(q, sentence)
                if corrected.query != q:
                    print("Did you mean:", corrected.string)
                query = corrected.query
                q_str = corrected.string
            else:
                query = q
                info = sentence
            results = [r['body'] for r in s.search(query, terms=True)]
        if not results:
            # nothing was found, adding ~ to each word
            # very ugly solution, maybe we can use Whoosh stemming abilities
            # http://whoosh.readthedocs.io/en/latest/stemming.html
            chunks = sentence.split()
            sentence = '~ '.join(chunks)+'~' # add ~ to each word
            q = qp.parse(sentence)
            with ix.searcher() as s:
                query = q
                info = 'FUZZY ' + sentence
                results = [r['body'] for r in s.search(query, terms=True)]
                
        print('BM25F scoring:', info, '->', results)
            #print('terms matched:', [r.matched_terms() for r in results])
    #    with ix.searcher(weighting=scoring.TF_IDF()) as s:
    #        corrected = s.correct_query(q, sentence)
    #        if corrected.query != q:
    #            print("Did you mean:", corrected.string)
    #        results = s.search(q, terms=True)
    #        print('TD-IDF scoring:', sentence, '->', [r['body'] for r in results])
            #print('terms matched:', [r.matched_terms() for r in results])

        print('--------------')
if __name__ == "__main__":
    main()
