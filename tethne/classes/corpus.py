"""
A :class:`.Corpus` is a container for :class:`.Paper`\s.
"""

from collections import Counter, defaultdict
from itertools import chain
import hashlib
import copy
from math import log

from tethne.classes.feature import FeatureSet, Feature, \
                                   StructuredFeatureSet, StructuredFeature
from tethne.utilities import _iterable, argsort

import sys
import os
PYTHON_3 = sys.version_info[0] == 3
if PYTHON_3:
    unicode = str


def _tfidf(f, c, C, DC, N):
    tf = float(c)
    idf = log(float(N)/float(DC))
    return tf*idf


def _filter(s, C, DC):
    if C > 3 and DC > 1 and len(s) > 3:
        return True
    return False


class Corpus(object):
    """
    A :class:`.Corpus` represents a collection of :class:`.Paper` instances.

    .. autosummary::
       :toctree:
       :nosignatures:

       distribution
       feature_distribution
       features
       index
       index_by
       index_feature
       indexed_papers
       indices
       papers
       select
       slice
       subcorpus
       top_features

    :class:`.Corpus` objects are generated by the bibliographic readers in the
    :mod:`tethne.readers` module.

    .. code-block:: python

       >>> from tethne.readers.wos import read
       >>> read('/path/to/data')
       <tethne.classes.corpus.Corpus object at 0x10278ea10>

    You can also build a :class:`.Corpus` from a list of :class:`.Paper`\s.

    .. code-block:: python

       >>> papers = however_you_generate_papers()   # <- list of Papers.
       >>> corpus = Corpus(papers)

    All of the :class:`.Paper`\s in the :class:`.Corpus` will be indexed. You
    can control which field is used for indexing by passing the ``index_by``
    keyword argument to one of the ``read`` methods or to the :class:`.Corpus`
    constructor.

    .. code-block:: python

       >>> corpus = Corpus(papers, index_by='doi')
       >>> corpus.indexed_papers.keys()
       ['doi/123', 'doi/456', ..., 'doi/789']

    The WoS ``read`` method uses the ``wosid`` field by default, and the DfR
    ``read`` method uses ``doi``. The Zotero ``read`` method tries to use
    whatever it can find. If the selected ``index_by`` field is not set or not
    available, a unique key will be generated using the title and author names.

    By default, :class:`.Corpus` will also index the ``authors`` and
    ``citations`` fields. To control which fields are indexed, pass the
    ``index_fields`` argument, or call :meth:`.Corpus.index` directly.

    .. code-block:: python

       >>> corpus = Corpus(papers, index_fields=['authors', 'date'])
       >>> corpus.indices.keys()
       ['authors', 'date']

    Similarly, :class:`.Corpus` will index features. By default, ``authors``
    and ``citations`` will be indexed as features (i.e. available for
    network-building methods). To control which fields are indexed as features,
    pass the ``index_features`` argument, or call
    :meth:`.Corpus.index_features`\.

    .. code-block:: python

       >>> corpus = Corpus(papers, index_features=['unigrams'])
       >>> corpus.features.keys()
       ['unigrams']

    There are a variety of ways to select :class:`.Paper`\s from the corpus.

    .. code-block:: python

       >>> corpus = Corpus(papers)
       >>> corpus[0]    # Integer indices yield a single Paper.
       <tethne.classes.paper.Paper object at 0x103037c10>

       >>> corpus[range(0,5)]  # A list of indices will yield a list of Papers.
       [<tethne.classes.paper.Paper object at 0x103037c10>,
        <tethne.classes.paper.Paper object at 0x10301c890>,
        ...
        <tethne.classes.paper.Paper object at 0x10302f5d0>]

       >>> corpus[('date', 1995)]  # You can select based on indexed fields.
       [<tethne.classes.paper.Paper object at 0x103037c10>,
        <tethne.classes.paper.Paper object at 0x10301c890>,
        ...
        <tethne.classes.paper.Paper object at 0x10302f5d0>]

       >>> corpus['citations', ('DOLE RJ 1952 CELL')]   # All papers with this citation!
       [<tethne.classes.paper.Paper object at 0x103037c10>,
        <tethne.classes.paper.Paper object at 0x10301c890>,
        ...
        <tethne.classes.paper.Paper object at 0x10302f5d0>]

       >>> corpus[('date', range(1993, 1995))]  # Multiple values are supported, too.
       [<tethne.classes.paper.Paper object at 0x103037c10>,
        <tethne.classes.paper.Paper object at 0x10301c890>,
        ...
        <tethne.classes.paper.Paper object at 0x10302f5d0>]

    If you prefer to retrieve a :class:`.Corpus` rather than simply a list of
    :class:`.Paper` instances (e.g. to build networks), use
    :meth:`.Corpus.subcorpus`\. ``subcorpus`` accepts selector arguments
    just like :meth:`.Corpus.__getitem__`\.

    .. code-block:: python

       >>> corpus = Corpus(papers)
       >>> subcorpus = corpus.subcorpus(('date', 1995))
       >>> subcorpus
       <tethne.classes.corpus.Corpus object at 0x10278ea10>

    """
    @property
    def papers(self):
        """
        A list of all :class:`.Paper`\s in the :class:`.Corpus`\.
        """
        return list(self.indexed_papers.values())

    index_by = None
    """
    Specifies the field in :class:`.Paper`\s that should be used as the
    primary indexing field for a :class:`.Corpus` instance.
    """

    index_class = dict
    index_kwargs = {}
    indexed_papers = {}
    """
    The primary index for :class:`.Paper`\s in a :class:`.Corpus` instance.
    Keys are based on :attr:`.index_by`\, and values are :class:`.Paper`
    instances.
    """

    features = {}
    """
    Contains :class:`.FeatureSet`\s for a :class:`.Corpus` instance.

    New :class:`.FeatureSet`\s can be created from attributes of :class:`.Paper`
    using :meth:`.index_feature`\.
    """

    indices = {}
    """
    Contains field indices for the :class:`Paper`\s in a :class:`.Corpus`
    instance.

    The ``'citations'`` index, for example, allows us to look up all of the
    Papers that contain a particular bibliographic reference:

    .. code-block:: python

       >>> for citation, papers in corpus.indices['citations'].items()[7:10]:
       ...     print 'The following Papers cite {0} \\n\\n\\t{1} \\n'.format(citation, '\\n\\t'.join(papers))
       The following Papers cite WHITFIELD J 2006 NATURE:
            WOS:000252758800011
            WOS:000253464000004
       The following Papers cite WANG T 2006 GLOBAL CHANGE BIOL:
            WOS:000282225000019
            WOS:000281546800001
            WOS:000251903200006
            WOS:000292901400010
            WOS:000288656800015
            WOS:000318353300001
            WOS:000296710600017
            WOS:000255552100006
            WOS:000272153800012
       The following Papers cite LINKOSALO T 2009 AGR FOREST METEOROL:
            WOS:000298398700003

    Notice that the values above are not Papers themselves, but identifiers.
    These are the same identifiers used in the primary index, so we can use them
    to look up :class:`Paper`\s:

       >>> papers = corpus.indices['citations']['CARLSON SM 2004 EVOL ECOL RES']  # Who cited Carlson 2004?
       >>> print papers
       >>> for paper in papers:
       ...     print corpus.indexed_papers[paper]
       ['WOS:000311994600006', 'WOS:000304903100014', 'WOS:000248812000005']
       <tethne.classes.paper.Paper object at 0x112d1fe10>
       <tethne.classes.paper.Paper object at 0x1121e8310>
       <tethne.classes.paper.Paper object at 0x1144ad390>

    You can create new indices using :meth:`.index`.
    """

    def __init__(self, papers=[], index_by=None,
                 index_fields=['authors', 'citations', 'ayjid', 'date'],
                 index_features=['authors', 'citations'], **kwargs):
        """
        Parameters
        ----------
        paper : list
        index_by : str
        index_fields : str or iterable of strs
        kwargs : kwargs

        """

        self.index_by = index_by
        self.slices = []
        self.indices = {}
        self.features = {}
        self.duplicate_papers = {}
        self.indices = defaultdict(dict)
        self.indices_lookup = defaultdict(dict)
        if index_by not in index_fields:
            index_fields.append(index_by)
        self.index_fields = index_fields
        self.index_features = index_features

        if self.index_class is dict:
            self.indexed_papers = {}
        else:
            self.indexed_papers = self.index_class(**self.index_kwargs)
        for field in self.index_features:
            if field not in self.features:
                self._init_featureset(field)

        for paper in papers:
            self._index_paper(paper)

    def add_papers(self, papers):
        for paper in papers:
            self._index_paper(paper)

    def __len__(self):
        return len(self.indexed_papers)

    def _index_paper(self, paper):
        key = self._generate_index(paper)

        # if key not in self.indexed_papers.keys():

        self.indexed_papers[key] = paper
        for field in self.index_fields:
            if field:
                self.index_paper_by_attr(paper, field)
        for field in self.index_features:
            if field:
                self.index_paper_by_feature(paper, field)
        # else:
        #     if not self.duplicate_papers:
        #         self.duplicate_papers = {key:2}
        #     else:
        #         if key not in self.duplicate_papers.keys():
        #             count = 1
        #         else:
        #             count = self.duplicate_papers[key]
        #         self.duplicate_papers.update({self._generate_index(paper): count+1})

    def _generate_index(self, paper):
        """
        If the ``index_by`` field is not set or not available, generate a unique
        identifier using the :class:`.Paper`\'s title and author names.
        """
        if self.index_by is None or not hasattr(paper, self.index_by):
            if not hasattr(paper, 'hashIndex'): # Generate a new index for this paper.
                m = hashlib.md5()

                # If we dont have author name then we just use the title of the paper
                # to generate unique identifier.
                if paper.authors is None:
                    hashable = paper.title
                else:
                    if hasattr(paper, 'title'):
                        title = paper.title
                    else:
                        title = ''
                    if len(paper.authors) == 0:
                        hashable = title
                    else:
                        authors = list(zip(*paper.authors))[0]
                        hashable = u' '.join(list([title] + [l + f for l, f in authors]))

                m.update(hashable.encode('utf-8'))
                setattr(paper, 'hashIndex', m.hexdigest())
            return getattr(paper, 'hashIndex')
        identifier = getattr(paper, self.index_by)
        if type(identifier) is list:
            identifier = identifier[0]
        if self.index_by == 'link':
            _, identifier = os.path.split(identifier)
        return identifier    # Identifier is already available.

    def _init_featureset(self, feature_name, structured=False):
        if structured:
            fsclass = StructuredFeatureSet
        else:
            fsclass = FeatureSet

        self.features[feature_name] = fsclass()

    def index_paper_by_feature(self, paper, feature_name, tokenize=lambda x: x,
                               structured=False):
        if not feature_name:
            return

        if structured:
            fclass = StructuredFeature
        else:
            fclass = Feature

        if hasattr(paper, feature_name):
            i = self._generate_index(paper)
            feature = fclass(tokenize(copy.deepcopy(getattr(paper, feature_name))))

            self.features[feature_name].add(i, feature)

    def index_feature(self, feature_name, tokenize=lambda x: x, structured=False):
        """
        Creates a new :class:`.FeatureSet` from the attribute ``feature_name``
        in each :class:`.Paper`\.

        New :class:`.FeatureSet`\s are added to :attr:`.features`\.

        Parameters
        ----------
        feature_name : str
            The name of a :class:`.Paper` attribute.

        """
        self._init_featureset(feature_name, structured=structured)

        for paper in self.papers:
            self.index_paper_by_feature(paper, feature_name, tokenize, structured)

    def index_paper_by_attr(self, paper, attr):
        i = self._generate_index(paper)
        if not attr:
            return

        if hasattr(paper, attr):
            value = copy.deepcopy(getattr(paper, attr))
            for v in _iterable(value):
                if type(value) is Feature:
                    v_ = v[:-1]
                else:
                    v_ = v

                if hasattr(v_, '__iter__'):
                    if len(v_) == 1:
                        t = type(v_[0])
                        v_ = t(v_[0])

                if v_ not in self.indices[attr]:
                    self.indices[attr][v_] = []
                self.indices[attr][v_].append(i)

                # For more efficient lookup later.
                if attr not in self.indices_lookup[i]:
                    self.indices_lookup[i][attr] = []
                self.indices_lookup[i][attr].append(v_)

    def index(self, attr):
        """
        Indexes the :class:`.Paper`\s in this :class:`.Corpus` instance
        by the attribute ``attr``.

        New indices are added to :attr:`.indices`\.

        Parameters
        ----------
        attr : str
            The name of a :class:`.Paper` attribute.

        """

        for i, paper in self.indexed_papers.iteritems():
            self.index_paper_by_attr(paper, attr)


    def __getitem__(self, selector):
        return self.select(selector)

    def __getattr__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        elif key in self.indices:
            return self.indices[key]
        raise AttributeError("Corpus has no such attribute")

    def select(self, selector, index_only=False):
        """
        Retrieves a subset of :class:`.Paper`\s based on selection criteria.

        There are a variety of ways to select :class:`.Paper`\s.

        .. code-block:: python

           >>> corpus = Corpus(papers)
           >>> corpus[0]    # Integer indices yield a single Paper.
           <tethne.classes.paper.Paper object at 0x103037c10>

           >>> corpus[range(0,5)]  # A list of indices yields a list of Papers.
           [<tethne.classes.paper.Paper object at 0x103037c10>,
            <tethne.classes.paper.Paper object at 0x10301c890>,
            ...
            <tethne.classes.paper.Paper object at 0x10302f5d0>]

           >>> corpus[('date', 1995)]  # Select based on indexed fields.
           [<tethne.classes.paper.Paper object at 0x103037c10>,
            <tethne.classes.paper.Paper object at 0x10301c890>,
            ...
            <tethne.classes.paper.Paper object at 0x10302f5d0>]

           >>> corpus['citations', ('DOLE RJ 1952 CELL')]   # Citing papers!
           [<tethne.classes.paper.Paper object at 0x103037c10>,
            <tethne.classes.paper.Paper object at 0x10301c890>,
            ...
            <tethne.classes.paper.Paper object at 0x10302f5d0>]

           >>> corpus[('date', range(1993, 1995))] # Multiple values are OK.
           [<tethne.classes.paper.Paper object at 0x103037c10>,
            <tethne.classes.paper.Paper object at 0x10301c890>,
            ...
            <tethne.classes.paper.Paper object at 0x10302f5d0>]

        If you prefer to retrieve a :class:`.Corpus` rather than simply a
        list of :class:`.Paper` instances (e.g. to build networks), use
        :meth:`.Corpus.subcorpus`\.

        Parameters
        ----------
        selector : object
            See method description.

        Returns
        -------
        list
            A list of :class:`.Paper`\s.
        """

        papers = []
        if type(selector) is tuple: # Select papers by index.
            index, value = selector
            if type(value) is list:  # Set of index values.
                papers = [p for v in value for p in self.select((index, v), index_only=index_only)]
            else:
                if value in self.indices[index]:
                    if index_only:
                        papers = self.indices[index][value]
                    else:
                        papers = [self.indexed_papers[p] for p  # Single index value.
                                  in self.indices[index][value]]
                else:
                    papers = []
        elif type(selector) is list:
            if selector[0] in self.indexed_papers:
                # Selector is a list of primary indices.
                if index_only:
                    papers = selector
                else:
                    papers = [self.indexed_papers[s] for s in selector]
            elif type(selector[0]) is int:
                if index_only:
                    papers = [self.indexed_papers.keys()[i] for i in selector]
                else:
                    papers = [self.papers[i] for i in selector]
        elif type(selector) is int:
            if index_only:
                papers = self.indexed_papers.keys()[selector]
            else:
                papers = self.papers[selector]

        elif type(selector) in [str, unicode]:
            if selector in self.indexed_papers:
                if index_only:
                    papers = selector
                else:
                    papers = self.indexed_papers[selector]
        return papers

    def slice(self, window_size=1, step_size=1, cumulative=False,
              count_only=False, subcorpus=True, feature_name=None):
        """
        Returns a generator that yields ``(key, subcorpus)`` tuples for
        sequential time windows.

        Two common slicing patterns are the "sliding time-window" and the
        "time-period" patterns. Whereas time-period slicing divides the corpus
        into subcorpora by sequential non-overlapping time periods, subcorpora
        generated by time-window slicing can overlap.

        .. figure:: _static/images/bibliocoupling/timeline.timeslice.png
           :width: 400
           :align: center

           **Time-period** slicing, with a window-size of 4 years.

        .. figure:: _static/images/bibliocoupling/timeline.timewindow.png
           :width: 400
           :align: center

           **Time-window** slicing, with a window-size of 4 years and a
           step-size of 1 year.

        *Sliding time-window* -- Set ``step_size=1``, and ``window_size`` to
        the desired value.
        *Time-period* -- ``step_size`` and ``window_size`` should have the same
        value.

        The value of ``key`` is always the first year in the slice.

        Examples
        --------
        .. code-block:: python

           >>> from tethne.readers.wos import read
           >>> corpus = read('/path/to/data')
           >>> for key, subcorpus in corpus.slice():
           ...     print key, len(subcorpus)
           2005, 5
           2006, 5

        Parameters
        ----------
        window_size : int
            (default: 1) Size of the time window, in years.
        step_size : int
            (default: 1) Number of years to advance window at each step.

        Returns
        -------
        generator
        """

        if 'date' not in self.indices:
            self.index('date')

        start = min(self.indices['date'].keys())
        end = max(self.indices['date'].keys())

        while start <= end - (window_size - 1):
            selector = ('date', range(start, start + window_size, 1))
            if cumulative:
                year = start + window_size
            else:
                year = start
            if count_only:
                yield year, len(self.select(selector))
            elif feature_name:
                yield year, self.subfeatures(selector, feature_name)
            elif subcorpus:
                yield year, self.subcorpus(selector)
            else:
                yield year, self.select(selector)
            if cumulative:
                window_size += step_size
            else:
                start += step_size

    def distribution(self, **slice_kwargs):
        """
        Calculates the number of papers in each slice, as defined by
        ``slice_kwargs``.

        Examples
        --------
        .. code-block:: python

           >>> corpus.distribution(step_size=1, window_size=1)
           [5, 5]

        Parameters
        ----------
        slice_kwargs : kwargs
            Keyword arguments to be passed to :meth:`.Corpus.slice`\.

        Returns
        -------
        list
        """
        values = []
        keys = []

        for key, size in self.slice(count_only=True, **slice_kwargs):
            values.append(size)
            keys.append(key)
        return keys, values

    def feature_distribution(self, featureset_name, feature, mode='counts',
                             **slice_kwargs):
        """
        Calculates the distribution of a feature across slices of the corpus.

        Examples
        --------
        .. code-block:: python

           >>> corpus.feature_distribution(featureset_name='citations', \
           ...                             feature='DOLE RJ 1965 CELL', \
           ...                             step_size=1, window_size=1)
           [2, 15, 25, 1]

        Parameters
        ----------
        featureset_name : str
            Name of a :class:`.FeatureSet` in the :class:`.Corpus`\.
        feature : str
            Name of the specific feature of interest. E.g. if
            ``featureset_name='citations'``, then ``feature`` could be
            something like ``'DOLE RJ 1965 CELL'``.
        mode : str
            (default: ``'counts'``) If set to ``'counts'``, values will be the
            sum of all count values for the feature in each slice. If set to
            ``'documentCounts'``, values will be the number of papers in which
            the feature occurs in each slice.
        slice_kwargs : kwargs
            Keyword arguments to be passed to :meth:`.Corpus.slice`\.

        Returns
        -------
        list
        """

        values = []
        keys = []
        fset = self.features[featureset_name]

        for key, papers in self.slice(subcorpus=False, **slice_kwargs):
            allfeatures = [v for v
                           in chain(*[fset.features[self._generate_index(p)]
                                      for p in papers
                                      if self._generate_index(p)
                                      in fset.features])]

            if len(allfeatures) < 1:
                keys.append(key)
                values.append(0.)
                continue

            count = 0.
            for elem, v in allfeatures:
                if elem != feature:
                    continue
                if mode == 'counts':
                    count += v
                else:
                    count += 1.
            values.append(count)
            keys.append(key)
        return keys, values

    def top_features(self, featureset_name, topn=20, by='counts',
                     perslice=False, slice_kwargs={}):
        """
        Retrieves the top ``topn`` most numerous features in the corpus.

        Parameters
        ----------
        featureset_name : str
            Name of a :class:`.FeatureSet` in the :class:`.Corpus`\.
        topn : int
            (default: ``20``) Number of features to return.
        by : str
            (default: ``'counts'``) If ``'counts'``, uses the sum of feature
            count values to rank features. If ``'documentCounts'``, uses the
            number of papers in which features occur.
        perslice : bool
            (default: False) If True, retrieves the top ``topn`` features in
            each slice.
        slice_kwargs : kwargs
            If ``perslice=True``, these keyword arguments are passed to
            :meth:`.Corpus.slice`\.
        """

        if perslice:
            return [(k, subcorpus.features[featureset_name].top(topn, by=by))
                    for k, subcorpus in self.slice(**slice_kwargs)]
        return self.features[featureset_name].top(topn, by=by)

    def subfeatures(self, selector, featureset_name):
        indices = self.select(selector, index_only=True)
        fclass = self.features[featureset_name].__class__

        return fclass({k:f for k,f in self.features[featureset_name].iteritems()
                           if k in indices})


    def subcorpus(self, selector):
        """
        Generates a new :class:`.Corpus` using the criteria in ``selector``.

        Accepts selector arguments just like  :meth:`.Corpus.select`\.

        .. code-block:: python

           >>> corpus = Corpus(papers)
           >>> subcorpus = corpus.subcorpus(('date', 1995))
           >>> subcorpus
           <tethne.classes.corpus.Corpus object at 0x10278ea10>

        """
        subcorpus = self.__class__(self[selector],
                           index_by=self.index_by,
                           index_fields=self.indices.keys(),
                           index_features=self.features.keys())

        return subcorpus
