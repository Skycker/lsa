# -*- coding: UTF-8 -*-
import collections
from random import choice
from stops import STOP_WORDS, EXCLUDE_CHARS
from nltk.stem import SnowballStemmer
import numpy as np
import helpers


class LSA(object):
    def __init__(self, latent_dimensions=2):
        """
        Args:
           latent_dimensions: numbers of dimensions which provide reliable indexing (but less than number of
            indexed words). For visualisation enough 2 dem.

        """

        self.latent_dimensions = latent_dimensions
        self.stop_words = STOP_WORDS
        self.chars_to_exclude = EXCLUDE_CHARS
        self.stemmer = SnowballStemmer(language="russian")
        self.docs = {}  # keeps documents and their ids
        self.words = []  # keeps indexed words
        self.keys = []  # keeps documents ids

    def exclude_trash(self, document):
        for char in self.chars_to_exclude:
            document = document.replace(char, ' ')
        return document

    def exclude_stops(self, document):
        return ' '.join([word for word in document.split(' ') if word not in self.stop_words])

    def stem_document(self, document, return_text=False):
        # we need if w to avoid empty strings in results
        stemmed_words = [self.stemmer.stem(w) for w in document.split(' ') if w]
        if return_text:
            return ' '.join(stemmed_words)
        return stemmed_words

    def prepare_document(self, document):
        document = helpers.lower_document(document)
        document = self.exclude_trash(document)
        document = self.exclude_stops(document)
        document = self.stem_document(document)
        return document

    def check_latent_dimensions(self):
        """ Check if entered by user latent dimensions (k) less than number of indexed words and documents """
        self.latent_dimensions = min(self.latent_dimensions, len(self.words), len(self.keys))

    def manage_repeating_words(self):
        """ List with indexed words should not have repeated entries """
        self.words = list(set(self.words))

    def manage_unique_words(self):
        """
        If some word has only one entry in documents we can leave it.
        This helps to save memory

        """
        counters = [collections.Counter(self.docs[key]) for key in self.keys]
        to_remove = []
        for word in self.words:
            cnt = 0
            for counter in counters:
                cnt += counter[word]
            if cnt <= 1:
                to_remove.append(word)
        self.words = list(set(self.words) - set(to_remove))

    def add_document(self, raw_document, document_id=None):
        # here documents is a list with stemmed words
        document = self.prepare_document(raw_document)
        key = document_id or len(self.docs) + 1  # проверять уникальность ключей
        self.keys.append(key)
        self.docs[key] = document
        self.words.extend(document)
        self.manage_repeating_words()

    def build_base_matrix(self):
        """
        Terms-to-documents matrix:
            Rows - indexed words
            Columns - documents

        At the intersection - how many times the word entry in the text

        """

        lst = []
        for word in self.words:
            row = []
            for key in self.keys:
                # Можно не создавать на каждом шаге объекты-счетчики, сделать это только один раз
                counter = collections.Counter(self.docs[key])
                row.append(counter[word])
            lst.append(row)

        self.X = np.matrix(lst)

    def svd(self):
        """ Singular Value Decomposition of base matrix """

        T, S, D = np.linalg.svd(self.X, full_matrices=True)

        # numpy returns S as flat array of diagonal elements (+ round):
        self.T = T.round(decimals=2)
        self.S = np.diag(S).round(decimals=2)
        self.D = D.round(decimals=2)

    def truncate_matrices(self):
        """ Truncate T, S and D matrices within latent_dimensions number
            The more dimensions, the bigger influence of 'noises'
            The less dimensions, the less semantic groups model can find

        """

        self.check_latent_dimensions()

        self.T = helpers.truncate_columns(self.T, self.latent_dimensions)
        self.D = helpers.truncate_rows(self.D, self.latent_dimensions)

        self.S = helpers.truncate_rows(self.S, self.latent_dimensions)
        self.S = helpers.truncate_columns(self.S, self.latent_dimensions)

    def recalculate_base_matrix(self):
        """ Rebuilding matrix X after truncating T, S and D """

        self.X = (self.T * self.S * self.D).round(decimals=2)

    def build_semantic_space(self, manage_unique=True):
        if manage_unique:
            self.manage_unique_words()
        self.build_base_matrix()
        self.svd()
        self.truncate_matrices()
        self.recalculate_base_matrix()

    def draw_semantic_space(self, file_name='semantic_space.png'):
        import matplotlib.pyplot as plt
        from matplotlib import rc

        font = {'family': 'Verdana', 'weight': 'normal'}
        rc('font', **font)

        # coordinates of words
        words_coords = self.T.tolist()
        x = [x for [x, y] in words_coords]
        y = [y for [x, y] in words_coords]

        # coordinates of documents
        docs_coords = self.D.T.tolist()
        x1 = [x for [x, y] in docs_coords]
        y1 = [y for [x, y] in docs_coords]

        fig, ax = plt.subplots()
        plt.title('Семантическое пространство')
        # plt.xlabel(u'D1')
        # plt.ylabel(u'D2')
        ax.spines['bottom'].set_position('center')
        ax.spines['left'].set_position('center')
        ax.spines['top'].set_color('none')
        ax.spines['right'].set_color('none')
        plt.plot(x, y, 'ro', x1, y1, 'bs')
        for i, word in enumerate(self.words):
            ax.annotate(word, xy=(x[i], y[i]), xytext=(5, 5), textcoords='offset points', ha='left',
                        va=choice(['bottom', 'top']))
        for i, key in enumerate(self.keys):
            print(x1[i], y1[i], 'T%s' % key)
            print(self.docs[key])
            ax.annotate('T%s' % key, xy=(x1[i], y1[i]), xytext=(5, 5), textcoords='offset points', ha='left',
                        va=choice(['bottom', 'top']))

        fig.savefig(file_name)