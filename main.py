#!/usr/bin/env python
import os
import json
import csv
import ast

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
    print('Generating index in {}'.format(directory))
    schema = Schema(text_value=TEXT(stored=True), attribute_code=TEXT(stored=True))
    create_dir(directory)
    ix = index.create_in(directory, schema)
    writer = ix.writer()
    total = 0
    with open('domain_dictionary.csv', 'r') as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            text_value = row['text_value'].lower().strip()
            if text_value:
                writer.add_document(text_value=text_value, attribute_code=row['attribute_code'])
                total += 1
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
        expected = [a.get('code') for a in attrs1]
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

def perform_search(searcher, query_parser, sentence):
    result = []
    # debug search
    query = query_parser.parse(sentence)
    search_result = searcher.search(query, terms=True, limit=10)
    print('DEBUG search', search_result)
    while True:
        query = query_parser.parse(sentence)
        search_result = searcher.search(query, terms=True, limit=1)
        if not search_result:
            break
        else:
            result.append(search_result[0]['text_value'])
            _, matched_term_bytes = search_result[0].matched_terms()[0]
            matched_term = matched_term_bytes.decode('utf8')
            if matched_term not in sentence:
                raise ValueError('{} not in {}'.format(matched_term, sentence))
            sentence = sentence.replace(matched_term, ' ')
    return result

def main():
    ix = get_index(config.INDEXDIR_PATH)  # get document index

    # creating QueryParser
    qp = QueryParser("text_value", schema=ix.schema, group=OrGroup.factory(0.9))
    # we will use FuzzyTermPlugin if nothing was found with exact search
    qp.add_plugin(FuzzyTermPlugin())

    # test_data = SENTENCES
    test_data = get_test_data(config.TEST_DATA_CSV)

    for sentence, expected in test_data:
        with ix.searcher(weighting=scoring.PL2()) as s:
            results = perform_search(s, qp, sentence.lower())
        #if not results:
        #    # nothing was found, adding ~ to each word
        #    # very ugly solution, maybe we can use Whoosh stemming abilities
        #    # http://whoosh.readthedocs.io/en/latest/stemming.html
        #    chunks = sentence.split()
        #    sentence = '~ '.join(chunks) + '~'  # add ~ to each word
        #    q = qp.parse(sentence)
        #    with ix.searcher() as s:
        #        query = q
        #        info = 'FUZZY ' + sentence
        #        results = [(r['text_value'], r['attribute_code'], r.matched_terms()) for r in s.search(query, terms=True, limit=1)]

        print('BM25F scoring:', sentence, '->', results)
        try:
            assert expected == results
        except AssertionError as e:
            print('Sentence\t', sentence)
            print('Results\t', results)
            print('Expected\t', expected)
            raise e
        # print('terms matched:', [r.matched_terms() for r in results])
        #    with ix.searcher(weighting=scoring.TF_IDF()) as s:
        #        corrected = s.correct_query(q, sentence)
        #        if corrected.query != q:
        #            print("Did you mean:", corrected.string)
        #        results = s.search(q, terms=True)
        #        print('TD-IDF scoring:', sentence, '->', [r['body'] for r in results])
        # print('terms matched:', [r.matched_terms() for r in results])

        print('--------------')


if __name__ == "__main__":
    main()
