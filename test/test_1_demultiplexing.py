
import os
import dreem.util as util
import pandas as pd

from dreem import demultiplexing

import factory

module = 'demultiplexing'
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
len_barcode = 10
barcodes = factory.generate_barcodes(len_barcode, number_of_constructs, 3)
sections_start = [[0, 25],[0, 25, 50, 75]]
sections_end = [[25, 49],[25, 50, 75, 99]]
sections = [['{}_{}'.format(ss, se) for ss,se in zip(sections_start[n], sections_end[n])] for n in range(number_of_constructs)]
sample_profile = factory.make_sample_profile(constructs, sequences, number_of_reads, mutations, insertions, deletions, sections=sections, section_start=sections_start, section_end=sections_end, barcodes=barcodes, barcode_start=barcode_start)
test_files_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_files'))

input_dir = os.path.join(test_files_dir,'input')
prediction_dir = os.path.join(test_files_dir,'predicted_output')
output_dir = os.path.join(test_files_dir,'output')

module_input = os.path.join(input_dir, module)
module_predicted = os.path.join(prediction_dir, module)
module_output = test_files_dir

inputs = ['fastq','library']
outputs = ['demultiplexed_fastq']

# ### Create test files for `test set 1`
def test_make_files():
    if not os.path.exists(os.path.join(test_files_dir, 'input', module)):
        os.makedirs(os.path.join(test_files_dir, 'input', module))
    factory.generate_files(sample_profile, module, inputs, outputs, test_files_dir, sample_name)
    factory.assert_files_exist(sample_profile, module, inputs, input_dir, sample_name)
    factory.assert_files_exist(sample_profile, module, outputs, prediction_dir, sample_name)

# ## Test code for convolution algorithm for demultiplexing

def test_run():
    for sample in os.listdir(module_input):
        
        args = {
            'fastq1': '{}/{}_R1.fastq'.format(os.path.join(module_input,sample),sample),
            'fastq2': '{}/{}_R2.fastq'.format(os.path.join(module_input,sample),sample),
            'library': '{}/library.csv'.format(os.path.join(module_input,sample)),
            'out_dir': module_output
        }

        demultiplexing.run(**args)

def test_files_exists():        
    factory.assert_files_exist(sample_profile, module, outputs, output_dir, sample_name)

def test_all_files_are_equal():
    for sample in os.listdir(module_input):
        for pred, out in zip(os.listdir(os.path.join(module_predicted,sample)), os.listdir(os.path.join(module_output,'output',module,sample))):
            assert pred == out, 'The predicted output and the output files are not the same'
            predicted = util.fastq_to_df(os.path.join(module_predicted,sample,pred))
            predicted['from'] = 'predicted'
            output = util.fastq_to_df(os.path.join(module_output,'output',module,sample,out))
            output['from'] = 'output'
            both = pd.concat([predicted,output],axis=0, ignore_index=True)
            for idx, g in both.groupby('construct'):
                if len(g) < 2:
                    assert g['from'].iloc[0] == 'predicted', 'The output file is missing the construct {} for file {}/{}'.format(idx,sample,out)
                    assert g['from'].iloc[0] == 'output', 'The output file didn\'t filter out the construct {} for file {}/{}'.format(idx,sample,out)
            for idx, g in both.groupby('construct'):
                for c in both.columns:
                    if c != 'construct' and c != 'from':
                        assert g[c].unique().shape[0] == 1, 'The output file is not the same as the predicted output for sample {} and construct {}'.format(sample,idx)


import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import time


def convolution_test_speed():

    base_to_vector = {
        "A": [1, 0, 0, 0],
        "T": [0, 1, 0, 0],
        "C": [0, 0, 1, 0],
        "G": [0, 0, 0, 1]
    }

    ntry = 1000

    # Create random sequences and barcodes
    seqs = []
    barcodes = []
    for i in range(ntry):
        seq = factory.create_sequence(100)
        barcode = factory.create_sequence(5)

        barcode_start = np.random.randint(0, 90)

        seq = seq[:barcode_start] + barcode + seq[barcode_start+len(barcode):]

        # print(barcode)
        # print(seq)

        seq = [ base_to_vector[base] for base in seq]
        seq = np.array(seq).T

        barcode = [ base_to_vector[base] for base in barcode]
        barcode = np.array(barcode).T

        seqs.append(seq)
        barcodes.append(barcode)

    # Compute correlation and time it
    now = time.time()
    for i in range(ntry):

        corr = signal.correlate(seqs[i], barcodes[i], mode="valid", method="auto").squeeze()/barcode.shape[1]

        np.argmax(corr)

    plt.plot(corr)
    print(np.argmax(corr))
    print(time.time()-now, "[ms]")

