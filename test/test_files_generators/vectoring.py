

import numpy as np
import dreem 
import dreem.util as util
import pandas as pd
import os
import factory

# ### Create test files for ```test_set_1.py```
def make_files():
    module = 'vectoring'
    sample_name = 'test_set_1'
    number_of_constructs = 2
    number_of_reads = [10]*number_of_constructs
    mutations = [[[25]]*4+[[50,75]]*(n-4) for n in number_of_reads]
    length = 100
    reads = [[factory.create_sequence(length)]*number_of_reads[k] for k in range(number_of_constructs)]
    insertions = [[[]]*n for n in number_of_reads]
    deletions = [[[]]*n for n in number_of_reads]
    constructs = ['construct_{}'.format(i) for i in range(number_of_constructs)]
    barcode_start = 10
    barcodes = factory.generate_barcodes(8, number_of_constructs, 3)
    sections_start = [[0, 25, 50, 75]]*number_of_constructs
    sections_end = [[25, 50, 75, 99]]*number_of_constructs
    sections = [['{}_{}'.format(ss, se) for ss,se in zip(sections_start[n], sections_end[n])] for n in range(number_of_constructs)]

    sample_profile = factory.make_sample_profile(constructs, reads, number_of_reads, mutations, insertions, deletions, sections=sections, section_start=sections_start, section_end=sections_end, barcodes=barcodes, barcode_start=barcode_start)
    test_files_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),  '../..', 'test', 'test_files'))

    inputs = ['sam','fasta','library']
    outputs = ['bitvector']
    factory.generate_files(sample_profile, module, inputs, outputs, test_files_dir, sample_name)
    factory.assert_files_exist(sample_profile, module, inputs, outputs, test_files_dir, sample_name)
