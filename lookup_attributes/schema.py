from whoosh import fields
from whoosh.analysis import StandardAnalyzer

STOPWORDS = []

analyzer = StandardAnalyzer(minsize=1, stoplist=STOPWORDS)



schema = fields.Schema(text_value=fields.TEXT(stored=True,
                                              analyzer=analyzer),
                       word_bigrams=fields.TEXT(stored=True, field_boost=3.0),
                       attribute_code=fields.STORED,
                       node_id=fields.STORED)