import dreem, os
import dreem.util as util
import pandas as pd
import factory



sample_name = 'test_set_1'
module = 'pipeline'

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

inputs = ['fastq','demultiplexed_fastq','bitvector','samples_csv','library', 'clustering']
outputs = ['output']

sample_profile = factory.make_sample_profile(constructs, sequences, number_of_reads, mutations, insertions, deletions, sections=sections, section_start=sections_start, section_end=sections_end, barcodes=barcodes, barcode_start=barcode_start)
test_files_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_files'))

input_dir = os.path.join(test_files_dir,'input')
prediction_dir = os.path.join(test_files_dir,'predicted_output')
output_dir = os.path.join(test_files_dir,'output')

module_input = os.path.join(input_dir, module)
module_predicted = os.path.join(prediction_dir, module)
module_output = test_files_dir

# ### Create test files for `test set 1`
def test_make_files():
    if not os.path.exists(os.path.join(test_files_dir, 'input', module)):
        os.makedirs(os.path.join(test_files_dir, 'input', module))
    factory.generate_files(sample_profile, module, inputs, outputs, test_files_dir, sample_name)
    factory.assert_files_exist(sample_profile, module, inputs, input_dir, sample_name)
    factory.assert_files_exist(sample_profile, module, outputs, prediction_dir, sample_name)

def test_run():
    for sample in os.listdir(module_input):
        
        dreem.alignment.run(            
            fastq1 = '{}/{}_R1.fastq'.format(os.path.join(module_input,sample),sample),\
            fastq2 = '{}/{}_R2.fastq'.format(os.path.join(module_input,sample),sample),\
            fasta = '{}/reference.fasta'.format(os.path.join(module_input,sample)),\
            out_dir = module_output,\
            sample=sample
            )
        

def test_copy_prediction_as_results():
    factory.copy_prediction_as_results(module_predicted, os.path.join(module_output,'output',module))
        
def test_files_exists():        
    factory.assert_files_exist(sample_profile, module, outputs, output_dir, sample_name)

def test_all_files_are_equal():
    assert 1 == 0, 'Not implemented yet'

