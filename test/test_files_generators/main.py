
import numpy as np
import dreem 
import dreem.util as util
import pandas as pd
import os
import factory

def make_files():
    module = 'main'
    sample_name = 'test_set_1'
    number_of_constructs = 2
    number_of_reads = [10]*2
    mutations = [ [[]]+[[25]]+[[35]]+[[]]*4+[[37]]+[[32]]+[[33,36]] for n in number_of_reads ]
    insertions = [ [[]]*3+[[11]]+[[10, 21]]+[[]]*2+[[15]]+[[]]*2 for n in number_of_reads ]
    deletions = [ [[]]*5+[[2]]+[[4, 6]]+[[]]+[[3]]+[[]] for n in number_of_reads ]

    length = [50, 150]
    sequences = [[factory.create_sequence(length[k])]*number_of_reads[k] for k in range(number_of_constructs)]
    constructs = ['construct_{}'.format(i) for i in range(number_of_constructs)]
    barcode_start = 30
    barcodes = factory.generate_barcodes(10, number_of_constructs, 3)
    sections_start = [[0, 25],[0, 25, 50, 75]]
    sections_end = [[25, 49],[25, 50, 75, 99]]
    sections = [['{}_{}'.format(ss, se) for ss,se in zip(sections_start[n], sections_end[n])] for n in range(number_of_constructs)]

    sample_profile = factory.make_sample_profile(constructs, sequences, number_of_reads, mutations, insertions, deletions, sections=sections, section_start=sections_start, section_end=sections_end, barcodes=barcodes, barcode_start=barcode_start)
    test_files_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),  '../..', 'test', 'test_files'))

    inputs = ['fastq','demultiplexed_fastq','bitvector','samples_csv','library', 'clustering']
    outputs = ['output']
    factory.generate_files(sample_profile, module, inputs, outputs, test_files_dir, sample_name)
    factory.assert_files_exist(sample_profile, module, inputs, outputs, test_files_dir, sample_name)
