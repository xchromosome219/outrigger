"""
Find exons adjacent to junctions
"""
import pprint
import itertools
import os
import sqlite3

import gffutils
import pandas as pd

from ..io.gtf import transform
from ..io.common import JUNCTION_ID, EXON_START, EXON_STOP, CHROM, STRAND
from ..region import Region, STRANDS
from ..util import done, progress


UPSTREAM = 'upstream'
DOWNSTREAM = 'downstream'
DIRECTIONS = UPSTREAM, DOWNSTREAM
NOVEL_EXON = 'novel_exon'
OUTRIGGER_DE_NOVO = 'outrigger_de_novo'
MAX_DE_NOVO_EXON_LENGTH = 100

class ExonJunctionAdjacencies(object):
    """Annotate junctions with neighboring exon_cols (upstream or downstream)"""

    exon_types = 'exon', NOVEL_EXON

    def __init__(self, metadata, db, junction_id=JUNCTION_ID,
                 exon_start=EXON_START, exon_stop=EXON_STOP,
                 chrom=CHROM, strand=STRAND,
                 max_de_novo_exon_length=MAX_DE_NOVO_EXON_LENGTH):
        """Initialize class to get upstream/downstream exon_cols of junctions

        Parameters
        ----------
        metadata : pandas.DataFrame
            A table of splice junctions with the columns indicated by the
            variables `junction_id`, `exon_start`, `exon_stop`, `chrom`,
            `strand`
        db : gffutils.FeatureDB
            Gffutils Database of gene, transcript, and exon features.
        junction_id, exon_start, exon_stop, chrom, strand : str
            Columns in `metadata`
        """

        columns = junction_id, exon_start, exon_stop, chrom, strand

        for column in columns:
            if column not in metadata:
                raise ValueError('The required column {} is not in the splice '
                                 'junction dataframe'.format(column))

        self.metadata = metadata.set_index(junction_id)
        self.metadata = self.metadata.sort_index()

        self.junction_id = junction_id
        self.exon_start = exon_start
        self.exon_stop = exon_stop
        self.chrom = chrom
        self.strand = strand

        self.db = db

        self.max_de_novo_exon_length = max_de_novo_exon_length

    def detect_exons_from_junctions(self):
        """Find exons based on gaps in junctions"""
        junctions = pd.Series(self.metadata.index.map(Region),
                              name='region', index=self.metadata.index)
        junctions = junctions.to_frame()
        junctions['chrom'] = junctions['region'].map(lambda x: x.chrom)

        for chrom, df in junctions.groupby('chrom'):
            junction_pairs = itertools.combinations(df.iterrows(), 2)
            for (name1, row1), (name2, row2) in junction_pairs:
                junction1 = row1['region']
                junction2 = row2['region']

                strand1, strand2 = junction1.strand, junction2.strand

                if strand1 != strand2:
                    strand = None
                else:
                    strand = strand1

                start, stop = self.is_there_an_exon_here(junction1, junction2)
                if start:
                    progress('Found new exon between '
                             '{} and {}'.format(str(junction1),
                                                str(junction2)))
                    self.add_exon_to_db(chrom, start=start, stop=stop,
                                        strand=strand)

    def write_de_novo_exons(self, filename='novel_exons.gtf'):
        """Write all de novo exons to a gtf"""
        with open(filename, 'w') as f:
            for noveL_exon in self.db.features_of_type(NOVEL_EXON):
                f.write(str(noveL_exon) + '\n')

    def is_there_an_exon_here(self, junction1, junction2):
        """Check if there could be an exon between these two junctions

        Parameters
        ----------
        junction{1,2} : outrigger.Region
            Outrigger.Region objects

        Returns
        -------
        start, stop : (int, int) or (False, False)
            Start and stop of the new exon if it exists, else False, False
        """
        if junction1.overlaps(junction2):
            return False, False

        # These are junction start/stops, not exon start/stops
        # Move one nt upstream of starts for exon stops,
        # and one nt downstream of stops for exon starts.
        option1 = abs(junction1.stop - junction2.start) \
                  < self.max_de_novo_exon_length
        option2 = abs(junction2.stop - junction1.start) \
                  < self.max_de_novo_exon_length

        if option1:
            return junction1.stop + 1, junction2.start - 1
        elif option2:
            return junction2.stop + 1, junction1.start - 1
        return False, False


    def add_exon_to_db(self, chrom, start, stop, strand):
        if strand not in STRANDS:
            strand = None
        overlapping_genes = list(self.db.region(seqid=chrom, start=start,
                                                end=stop, strand=strand,
                                                featuretype='gene'))

        exon_id = 'exon:{chrom}:{start}-{stop}:{strand}'.format(
            chrom=chrom, start=start, stop=stop, strand=strand)

        if len(overlapping_genes) == 0:
            exon = gffutils.Feature(chrom, source=OUTRIGGER_DE_NOVO,
                                    featuretype=NOVEL_EXON, start=start,
                                    end=stop, strand=strand, id=exon_id)
            progress('\tAdded a novel exon ({}), located in an unannotated'
                     ' gene'.format(exon.id))
            self.db.update([exon], id_spec={'novel_exon': 'location_id'},
                           transform=transform)
            return

        de_novo_exons = [gffutils.Feature(
            chrom, source=OUTRIGGER_DE_NOVO, featuretype=NOVEL_EXON,
            start=start, end=stop, strand=g.strand, id=exon_id + g.strand,
            attributes=dict(g.attributes.items()))
                         for g in overlapping_genes]

        # Add all exons that aren't already there
        for exon in de_novo_exons:
            try:
                try:
                    gene_name = ','.join(exon.attributes['gene_name'])
                except KeyError:
                    try:
                        gene_name = ','.join(exon.attributes['gene_id'])
                    except KeyError:
                        gene_name = 'unknown_gene'
                try:
                    # Check that the non-novel exon doesn't exist already
                    self.db[exon_id + exon.strand]
                except gffutils.FeatureNotFoundError:
                    # print([dict(g.attributes.items()) for g in overlapping_genes])
                    self.db.update([exon], id_spec={'novel_exon': 'location_id'},
                                   transform=transform)
                    progress('\tAdded a novel exon ({}) in the gene {} '
                             '({})'.format(exon.id,
                                           ','.join(exon.attributes['gene_id']),
                                           gene_name))
            except sqlite3.IntegrityError:
                continue

    @staticmethod
    def _single_junction_exon_triple(direction_ind, direction, exon_id):
        """Create exon, direction, junction triples for an exon + its junctions

        Parameters
        ----------
        direction_ind : pandas.Series
            A boolean series of the indices of the junctions matching with the
            provided exon. The index of the series must be the junction ID
        direction : str
            The direction of the exon relative to the junctions, either
            "upstream" or "downstream"
        exon_id : str
            Unique identifier of the exon

        Returns
        -------
        triples : pandas.DataFrame
            A (n, 3) sized dataframe of an exon and its adjacent junctions
        """
        length = direction_ind.sum()

        exons = [exon_id] * length
        directions = [direction] * length
        junctions = direction_ind[direction_ind].index
        return pd.DataFrame(list(zip(exons, directions, junctions)),
                            columns=['exon', 'direction', 'junction'])

    @staticmethod
    def _to_stranded_transcript_adjacency(adjacent_in_genome, strand):
        """If negative strand, swap the upstream/downstream adjacency

        Parameters
        ----------
        adjacent_in_genome : dict
            dict of two keys, "upstream" and "downstream", mapping to a boolean
            series indicating whether the junction is upstream or downstream of
            a particular exon
        strand : "-" | "+"
            Positive or negative strand
        """
        if strand == '+':
            return {UPSTREAM: adjacent_in_genome[UPSTREAM],
                    DOWNSTREAM: adjacent_in_genome[DOWNSTREAM]}
        elif strand == '-':
            return {UPSTREAM: adjacent_in_genome[DOWNSTREAM],
                    DOWNSTREAM: adjacent_in_genome[UPSTREAM]}

    def _junctions_genome_adjacent_to_exon(self, exon):
        """Get indices of junctions next to an exon, in genome coordinates"""
        chrom_ind = self.metadata[self.chrom] == exon.chrom

        strand_ind = self.metadata[self.strand] == exon.strand

        upstream_in_genome = \
            chrom_ind & strand_ind \
            & (self.metadata[self.exon_stop] == exon.stop)
        downstream_in_genome = \
            chrom_ind & strand_ind & \
            (self.metadata[self.exon_start] == exon.start)
        return {UPSTREAM: upstream_in_genome, DOWNSTREAM: downstream_in_genome}

    def _adjacent_junctions_single_exon(self, exon):
        """Get junctions adjacent to this exon

        Parameters
        ----------
        exon : gffutils.Feature
            An item in

        """
        dfs = []
        adjacent_in_genome = self._junctions_genome_adjacent_to_exon(exon)
        adjacent_in_transcriptome = self._to_stranded_transcript_adjacency(
            adjacent_in_genome, exon.strand)

        exon_id = exon.id
        for direction, ind in adjacent_in_transcriptome.items():
            if ind.any():
                df = self._single_junction_exon_triple(ind, direction, exon_id)
                dfs.append(df)

        if len(dfs) > 0:
            return pd.concat(dfs, ignore_index=True)
        else:
            return pd.DataFrame()

    def neighboring_exons(self):
        """Get upstream and downstream exon_cols of each junction

        The "upstream" and "downstream" is relative to the **junction**, e.g.

            exonA   upstream    junctionX
            exonB   downstream    junctionX

        should be read as "exonA is upstream of juction X" and "exonB is
        downstream of junctionX"

        Use junctions defined in ``sj_metadata`` and exon_cols in ``db`` to create
        triples of (exon, direction, junction), which are read like
        (subject, object, verb) e.g. ('exon1', 'upstream', 'junction12'), for
        creation of a graph database.

        Parameters
        ----------
        sj_metadata : pandas.DataFrame
            A splice junction metadata dataframe with the junction id as the
            index, with  columns defined by variables ``exon_start`` and
            ``exon_stop``.
        db : gffutils.FeatureDB
            A database of gene annotations created by gffutils. Must have
            features of type "exon"
        exon_start : str, optional
            Name of the column in sj_metadata corresponding to the start of the
            exon
        exon_stop : str, optional
            Name of the column in sj_metadata corresponding to the end of the
            exon

        Returns
        -------
        junction_exon_triples : pandas.DataFrame
            A three-column dataframe describing the relationship of where an
            exon is relative to junctions
        """
        n_exons = sum(1 for _ in self.db.features_of_type(self.exon_types))

        dfs = []

        progress('Starting annotation of all junctions with known '
                 'neighboring exon_cols ...')
        for i, exon in enumerate(self.db.features_of_type(self.exon_types)):
            if (i + 1) % 10000 == 0:
                progress('\t{}/{} exons completed'.format(i + 1, n_exons))
            df = self._adjacent_junctions_single_exon(exon)
            dfs.append(df)
        junction_exon_triples = pd.concat(dfs, ignore_index=True)
        done()
        return junction_exon_triples
