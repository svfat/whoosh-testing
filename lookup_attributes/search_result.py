from whoosh.analysis import StandardAnalyzer
from collections import Counter

from .field_names import TEXT_FIELD
from .schema import analyzer

# from .stopwords import STOPWORDS
STOPWORDS = []


def compute_tf(text):
    tf_text = Counter(text)
    for i in tf_text:
        tf_text[i] = tf_text[i] / float(len(text))
    return tf_text


class SearchResult:
    def __init__(self, text, attribute, matched, ix, initial_score=0):
        self._text = text
        self._attribute = attribute
        self._matched = matched
        self._initial_score = initial_score
        self._ix = ix
        self._tf = compute_tf(self.tokens)
        self._score = self._calculate_score()

    def __str__(self):
        return self.text

    def __repr__(self):
        return "<MagiaTerm(score={}, text={}, matched={}>".format(self.score, self.text, self.matched)

    @property
    def tokens(self):
        return [t.text for t in analyzer(self.text)]

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
        n = parent.doc_frequency(TEXT_FIELD, text)
        dc = parent.doc_count_all()
        return log(dc / (n + 1)) + 1

    def tf(self, token):
        return self._tf[token]

    def _calculate_score(self):
        # all_tokens_matched = all([token in self.matched for token in self.tokens])
        # if all_tokens_matched:
        #    return 100
        # print("matched_tokens=",self.matched)
        # not_matched_tokens = list(set([token for token in self.tokens if token.encode() not in self.matched]))
        not_matched_tokens = list(set([token for token in self.tokens if token not in self.matched]))

        # print("not_matched_tokens=", not_matched_tokens)
        with self._ix.searcher() as s:
            # sum_not_matched = sum([s.frequency(self._field_name, token) for token in not_matched_tokens])
            # sum_not_matched = sum([self.tf(token)*self.idf(s, token) for token in not_matched_tokens])

            # currently have to divide by len(doc_word_list) because not all tokens are showing
            # doc_word_list = set(str(self).replace('-', ' ').split())
            sum_not_matched = sum([self.tf(token) * self.idf(s, token) for token in not_matched_tokens])

        # base_bonus = 1 if self._attribute == 'brand' else 2
        base_bonus = 1
        score = self._initial_score * base_bonus
        if not_matched_tokens:
            # score -= sum_not_matched / len(not_matched_tokens)
            score -= sum_not_matched

        print(str(self), "  self.tokens=", self.tokens, " initial=", self._initial_score, " sum_not_matches=",
              sum_not_matched, " score=", score)
        # return score * -1
        return score

    def items(self):
        return self.score, self.text, self.matched
