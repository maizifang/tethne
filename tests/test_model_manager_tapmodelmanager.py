from settings import *

# Profiling.
from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

import unittest

from nltk.corpus import stopwords
import numpy
import os
from networkx import DiGraph

from tethne import DataCollection, GraphCollection, HDF5DataCollection
from tethne.readers import dfr
from tethne.model.managers import TAPModelManager, MALLETModelManager
from tethne.model import TAPModel
from tethne.networks.authors import coauthors

import cPickle as pickle
picklepath = '{0}/pickles'.format(datapath)
with open('{0}/dfr_DataCollection.pickle'.format(picklepath), 'r') as f:
    D = pickle.load(f)

class TestTAPModelManager(unittest.TestCase):
    def setUp(self):
        dfrdatapath = '{0}/dfr'.format(datapath)
        
        # Coauthor graph.
        self.G = GraphCollection()
        for k,v in D.get_slices('date', include_papers=True).iteritems():
            self.G[k] = coauthors(v)
        
        # LDAModel
        self.L = MALLETModelManager(D, outpath=outpath,
                                       temppath=temppath,
                                       mallet_path=mallet_path)
        self.L._load_model()
        
        if profile:
            pcgpath = cg_path + 'model.manager.TAPModelManager.__init__.png'
            with PyCallGraph(output=GraphvizOutput(output_file=pcgpath)):
                self.M = TAPModelManager(D, self.G, self.L.model,
                                                        outpath=outpath,
                                                        temppath=temppath,
                                                        mallet_path=mallet_path)
        else:
            self.M = TAPModelManager(D, self.G, self.L.model,
                                                    outpath=outpath,
                                                    temppath=temppath,
                                                    mallet_path=mallet_path)

    def test_author_theta(self):
        """
        Should generate an ``a_theta`` matrix for slice ``0`` with shape (3,20).
        """

        s = D.get_slices('date').keys()[0]
        papers = D.get_slice('date', s, include_papers=True)
        authors_list = list(set([ a for p in papers for a in p.authors() ]))
        authors = { authors_list[i]:i for i in xrange(len(authors_list)) }
        
        if profile:
            pcgpath = cg_path + 'model.manager.TAPModelManager.author_theta.png'
            with PyCallGraph(output=GraphvizOutput(output_file=pcgpath)):
                atheta = self.M.author_theta(papers, authors)
        else:
            atheta = self.M.author_theta(papers, authors)

        self.assertEqual(len(atheta), 3)
        self.assertIsInstance(atheta, dict)
        self.assertEqual(atheta[0].shape, (20,))

    def test_build_and_graph_collection(self):
        """
        :func:`.build` should generate a set of :class:`.TAPModel` instances.
        :func:`.graph_collection` should generate a :class:`.GraphCollection`\.
        """

        if profile:
            pcgpath = cg_path + 'model.manager.TAPModelManager.build.png'
            with PyCallGraph(output=GraphvizOutput(output_file=pcgpath)):
                self.M.build(axis='date')
        else:
            self.M.build(axis='date')

        self.assertIsInstance(self.M.SM.values()[0], TAPModel)
        self.assertIsInstance(self.M.SM.values()[0].MU[0], DiGraph)
        
        if profile:
            pcgpath = cg_path + 'model.manager.TAPModelManager.graph_collection.png'
            with PyCallGraph(output=GraphvizOutput(output_file=pcgpath)):
                GC = self.M.graph_collection(0)
        else:
            GC = self.M.graph_collection(0)

        self.assertIsInstance(GC, GraphCollection)

if __name__ == '__main__':
    unittest.main()