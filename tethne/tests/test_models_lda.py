import sys
sys.path.append('../tethne')

import unittest
import tempfile
import os
from xml.etree import ElementTree as ET
import networkx as nx
import csv

from tethne.model.corpus.mallet import LDAModel
from tethne.readers.wos import read
from tethne import FeatureSet, tokenize
from tethne.networks import topics

datapath = './tethne/tests/data/wos3.txt'


import logging
logger = logging.getLogger('mallet')
logger.setLevel('DEBUG')


class TestLDAModel(unittest.TestCase):
    def setUp(self):
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize, structured=True)
        self.model = LDAModel(corpus, featureset_name='abstract')
        self.model.fit(Z=20, max_iter=500)

    def test_ldamodel(self):
        dates, rep = self.model.topic_over_time(1)
        self.assertGreater(sum(rep), 0)
        self.assertEqual(len(dates), len(rep))

        self.assertIsInstance(self.model.phi, FeatureSet)
        self.assertIsInstance(self.model.theta, FeatureSet)

        self.assertIsInstance(self.model.list_topics(), list)
        self.assertGreater(len(self.model.list_topics()), 0)
        self.assertIsInstance(self.model.list_topic(0), list)
        self.assertGreater(len(self.model.list_topic(0)), 0)

    def test_networks(self):
        termGraph = topics.terms(self.model)
        self.assertGreater(termGraph.size(), 100)
        self.assertGreater(termGraph.order(), 10)

        topicGraph = topics.cotopics(self.model)
        self.assertGreater(topicGraph.size(), 5)
        self.assertGreater(topicGraph.order(), 0)

        paperGraph = topics.topic_coupling(self.model)
        self.assertGreater(paperGraph.size(), 100)
        self.assertGreater(paperGraph.order(), 20)


class TestLDAModelUnstructured(unittest.TestCase):
    def setUp(self):
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize)
        self.model = LDAModel(corpus, featureset_name='abstract')
        self.model.fit(Z=20, max_iter=500)

    def test_ldamodel(self):
        dates, rep = self.model.topic_over_time(1)
        self.assertGreater(sum(rep), 0)
        self.assertEqual(len(dates), len(rep))

        self.assertIsInstance(self.model.phi, FeatureSet)
        self.assertIsInstance(self.model.theta, FeatureSet)

        self.assertIsInstance(self.model.list_topics(), list)
        self.assertGreater(len(self.model.list_topics()), 0)
        self.assertIsInstance(self.model.list_topic(0), list)
        self.assertGreater(len(self.model.list_topic(0)), 0)

    def test_networks(self):
        termGraph = topics.terms(self.model)
        self.assertGreater(termGraph.size(), 100)
        self.assertGreater(termGraph.order(), 10)

        topicGraph = topics.cotopics(self.model)
        self.assertGreater(topicGraph.size(), 5)
        self.assertGreater(topicGraph.order(), 0)

        paperGraph = topics.topic_coupling(self.model)
        self.assertGreater(paperGraph.size(), 100)
        self.assertGreater(paperGraph.order(), 20)


class TestLDAModelWithTransformation(unittest.TestCase):
    def setUp(self):
        corpus = read(datapath, index_by='wosid')
        corpus.index_feature('abstract', tokenize)

        xf = lambda f, c, C, DC: c*3
        corpus.features['xf'] = corpus.features['abstract'].transform(xf)
        self.model = LDAModel(corpus, featureset_name='xf')
        self.model.fit(Z=20, max_iter=500)

    def test_ldamodel(self):
        dates, rep = self.model.topic_over_time(1)
        self.assertGreater(sum(rep), 0)
        self.assertEqual(len(dates), len(rep))

        self.assertIsInstance(self.model.phi, FeatureSet)
        self.assertIsInstance(self.model.theta, FeatureSet)

        self.assertIsInstance(self.model.list_topics(), list)
        self.assertGreater(len(self.model.list_topics()), 0)
        self.assertIsInstance(self.model.list_topic(0), list)
        self.assertGreater(len(self.model.list_topic(0)), 0)

    def test_networks(self):
        termGraph = topics.terms(self.model)
        self.assertGreater(termGraph.size(), 100)
        self.assertGreater(termGraph.order(), 10)

        topicGraph = topics.cotopics(self.model)
        self.assertGreater(topicGraph.size(), 5)
        self.assertGreater(topicGraph.order(), 0)

        paperGraph = topics.topic_coupling(self.model)
        self.assertGreater(paperGraph.size(), 100)
        self.assertGreater(paperGraph.order(), 20)


if __name__ == '__main__':
    unittest.main()
