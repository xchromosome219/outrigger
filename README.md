# PoshSplice

[![](https://img.shields.io/travis/olgabot/poshsplice.svg)](https://travis-ci.org/olgabot/poshsplice)[![](https://img.shields.io/pypi/v/poshsplice.svg)](https://pypi.python.org/pypi/poshsplice)

Exon ontology is an attempt to catalogue scripts used to annotate exons and their functions

* Free software: BSD license
* Documentation: https://olgabot.github.io/poshsplice

## Features

### Read HMMScan output

After running HMMScan, the output is extensive and helpful, but non-trivial to parse into a dataframe-style format
since the separators are variable lengths of spaces, and the domain descriptions also have spaces, so parsing is
ambiguous. Here's an example output file, of using the [RBFOX2](http://en.wikipedia.org/wiki/RBM9) protein sequence
as a query, and scanning against the Pfam-A (manually curated) families from the Pfam version 27:

```
#                                                                             --- full sequence --- -------------- this domain -------------   hmm coord   ali coord   env coord
# target name        accession   tlen query name            accession   qlen   E-value  score  bias   #  of  c-Evalue  i-Evalue  score  bias  from    to  from    to  from    to  acc description of target
#------------------- ---------- -----  -------------------- ---------- ----- --------- ------ ----- --- --- --------- --------- ------ ----- ----- ----- ----- ----- ----- ----- ---- ---------------------
Fox-1_C              PF12414.3     93 sp|O43251|RFOX2_HUMAN -            390   3.2e-39  133.2  29.5   1   2      0.23   6.7e+02    0.7   0.0    14    48   177   213   166   243 0.66 Calcitonin gene-related peptide regulator C terminal
Fox-1_C              PF12414.3     93 sp|O43251|RFOX2_HUMAN -            390   3.2e-39  133.2  29.5   2   2   8.9e-42   2.6e-38  130.2  27.3     2    93   265   362   264   362 0.97 Calcitonin gene-related peptide regulator C terminal
RRM_1                PF00076.17    70 sp|O43251|RFOX2_HUMAN -            390     8e-19   67.0   0.1   1   1   5.9e-22   1.7e-18   65.9   0.1     2    70   124   191   123   191 0.97 RNA recognition motif. (a.k.a. RRM, RBD, or RNP domain)
RRM_6                PF14259.1     70 sp|O43251|RFOX2_HUMAN -            390   2.4e-15   56.2   0.1   1   1   1.4e-18   4.3e-15   55.4   0.1     1    70   123   191   123   191 0.95 RNA recognition motif (a.k.a. RRM, RBD, or RNP domain)
RRM_5                PF13893.1     56 sp|O43251|RFOX2_HUMAN -            390   8.1e-11   41.6   0.1   1   1   5.9e-14   1.8e-10   40.5   0.1     1    54   137   193   137   195 0.90 RNA recognition motif. (a.k.a. RRM, RBD, or RNP domain)
RRM_3                PF08777.6    105 sp|O43251|RFOX2_HUMAN -            390     0.084   12.7   0.0   1   1   6.7e-05       0.2   11.5   0.0    17    79   136   202   127   206 0.83 RNA binding motif
#
# Program:         hmmscan
# Version:         3.1b1 (May 2013)
# Pipeline mode:   SCAN
# Query file:      /projects/ps-yeolab/genomes/pfam/release_27/ftp.sanger.ac.uk/pub/databases/Pfam/releases/Pfam27.0/RBFOX2_human.fasta
# Target file:     /projects/ps-yeolab/genomes/pfam/release_27/ftp.sanger.ac.uk/pub/databases/Pfam/releases/Pfam27.0/Pfam-A.hmm
# Option settings: hmmscan --domtblout RBFOX2_human_pfam.txt --noali --notextw /projects/ps-yeolab/genomes/pfam/release_27/ftp.sanger.ac.uk/pub/databases/Pfam/releases/Pfam27.0/Pfam-A.hmm /projects/ps-yeolab/genomes/pfam/release_27/ftp.sanger.ac.uk/pub/databases/Pfam/releases/Pfam27.0/RBFOX2_human.fasta
# Current dir:     /home/obotvinnik/ipython_notebook/miso
# Date:            Tue Jan 27 18:56:23 2015
# [ok]
```



### Splice site scoring

To use this feature, you must have [`BioPerl` installed](http://bioperl.org/wiki/Installing_BioPerl).