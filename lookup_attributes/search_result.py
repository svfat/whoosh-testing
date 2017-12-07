from whoosh.analysis import StandardAnalyzer
from collections import Counter

from .stopwords import STOPWORDS

def compute_tf(text):
    tf_text = Counter(text)
    for i in tf_text:
        tf_text[i] = tf_text[i]/float(len(text))
    return tf_text

class SearchResult:
    def __init__(self, text, matched, ix, field_name, initial_score=0):
        self._text = text
        self._matched = matched
        self._initial_score = initial_score
        self._analyzer = StandardAnalyzer(minsize=1, stoplist=STOPWORDS)
        self._ix = ix
        self._field_name = field_name
        self._tf = compute_tf(self.tokens)
        self._score = self._calculate_score()


    def __str__(self):
        return self.text

    def __repr__(self):
        return "<MagiaTerm(score={}, text={}, matched={}>".format(self.score, self.text, self.matched)

    @property
    def tokens(self):
        return [t.text for t in self._analyzer(self.text)]

    @property
    def score(self):
        return self._score

    @property
    def text(self):
        return self._text

    @property
    def matched(self):
        return [m.decode('utf-8') for m in self._matched]

    def idf(self, searcher, text):
        """Returns the inverse document frequency of the given term.
        """
        from math import log
        parent = searcher.get_parent()
        n = parent.doc_frequency(self._field_name, text)
        dc = parent.doc_count_all()
        return log(dc / (n + 1)) + 1

    def tf(self, token):
        return self._tf[token]

    def _calculate_score(self):
        #all_tokens_matched = all([token in self.matched for token in self.tokens])
        #if all_tokens_matched:
        #    return 100
        # print("matched_tokens=",self.matched)
        # not_matched_tokens = list(set([token for token in self.tokens if token.encode() not in self.matched]))
        doc_word_list = set(str(self).split())
        not_matched_tokens = list(set([token for token in doc_word_list if token not in self.matched]))

        # print("not_matched_tokens=", not_matched_tokens)
        with self._ix.searcher() as s:
            #sum_not_matched = sum([s.frequency(self._field_name, token) for token in not_matched_tokens])
            # maybe stopwords are being aggressively removed because 'red arts' only coming through as ['red']
            sum_not_matched = sum([(1/len(doc_word_list))*self.idf(s, token) for token in not_matched_tokens])

        score = self._initial_score
        if not_matched_tokens:
            # score -= sum_not_matched / len(not_matched_tokens)
            score -= sum_not_matched

        print("self.tokens=",self.tokens, " initial=",self._initial_score,  " sum_not_matches=", sum_not_matched," score=",score)
        #return score * -1
        return score

    def items(self):
        return self.score, self.text, self.matched
