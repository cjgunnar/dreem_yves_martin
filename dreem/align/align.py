import itertools
import os
import re
from typing import List, Optional

from core import FASTQC_CMD, CUTADAPT_CMD, BOWTIE2_CMD, PASTE_CMD, BASEN, \
    BOWTIE2_BUILD_CMD, TEMP_DIR, OUTPUT_DIR, run_cmd, check_fasta, sort_sam, \
    try_remove, index_bam, switch_directory, PHRED_ENCODING, SAMTOOLS_CMD

# General parameters
DEFAULT_INTERLEAVED = False
SAM_HEADER = b"@"
SAM_ALIGN_SCORE = b"AS:i:"
SAM_EXTRA_SCORE = b"XS:i:"

# FastQC parameters
DEFAULT_EXTRACT = False

# Cutadapt parameters
DEFAULT_MIN_BASE_QUALITY = 25
DEFAULT_ILLUMINA_ADAPTER = "AGATCGGAAGAGC"
DEFAULT_MIN_OVERLAP = 6
DEFAULT_MAX_ERROR = 0.1
DEFAULT_INDELS = True
DEFAULT_NEXTSEQ = True
DEFAULT_DISCARD_TRIMMED = False
DEFAULT_DISCARD_UNTRIMMED = False
DEFAULT_TRIM_CORES = os.cpu_count()
DEFAULT_MIN_LENGTH = 50

# Bowtie 2 parameters
DEFAULT_LOCAL = True
DEFAULT_UNALIGNED = False
DEFAULT_DISCORDANT = False
DEFAULT_MIXED = False
DEFAULT_DOVETAIL = False
DEFAULT_CONTAIN = True
DEFAULT_FRAG_LEN_MIN = 0
DEFAULT_FRAG_LEN_MAX = 300  # maximum length of a 150 x 150 read
DEFAULT_MAP_QUAL_MIN = 30
DEFAULT_N_CEIL = "L,0,0.05"
DEFAULT_SEED = 12
DEFAULT_EXTENSIONS = 6
DEFAULT_RESEED = 1
DEFAULT_PADDING = 4
DEFAULT_ALIGN_THREADS = os.cpu_count()
DEFAULT_METRICS = 60
MATCH_BONUS = "1"
MISMATCH_PENALTY = "-1,-1"
N_PENALTY = "0"
REF_GAP_PENALTY = "0,-1"
READ_GAP_PENALTY = "0,-1"
IGNORE_QUALS = True
SAM_EXT = ".sam"
BAM_EXT = ".bam"


class SequencingFileBase(object):
    __slots__ = ["_prj_dir", "_paired", "_encoding"]

    operation_dir = ""

    def __init__(self, project_dir: str,
                 paired: bool = False,
                 encoding: int = PHRED_ENCODING) -> None:
        self._prj_dir = project_dir
        self._paired = paired
        self._encoding = encoding
    
    @property
    def project_dir(self):
        return self._prj_dir
    
    @property
    def paired(self):
        return self._paired
    
    @property
    def encoding(self):
        return self._encoding
    
    @property
    def encoding_arg(self):
        return f"--phred{self.encoding}"
    
    def _get_output_dir(self, dirname):
        assert self.operation_dir
        return os.path.join(self.project_dir, dirname, self.operation_dir)
    
    @property
    def temp_dir(self):
        return self._get_output_dir(TEMP_DIR)
    
    @property
    def output_dir(self):
        return self._get_output_dir(OUTPUT_DIR)
    
    def to_temp_dir(self, file_path: str):
        return switch_directory(file_path, self.temp_dir)
    
    def to_output_dir(self, file_path: str):
        return switch_directory(file_path, self.output_dir)


class FastqBase(SequencingFileBase):
    __slots__ = ["_fq", "_fq2"]

    def __init__(self, project_dir: str, fastq: str,
                 fastq2: Optional[str] = None, paired: bool = False,
                 encoding: int = PHRED_ENCODING) -> None:
        super().__init__(project_dir, paired, encoding)
        self._fq = fastq
        self._fq2 = fastq2
        self._paired = paired or self._fq2 is not None
    
    @property
    def n_fastqs(self):
        return 1 if self._fq2 is None else 2
    
    def _verify_1_fastq(self):
        if self.n_fastqs == 2:
            raise ValueError("Two FASTQ files exist")
    
    def _verify_2_fastqs(self):
        if self.n_fastqs == 1:
            if self.interleaved:
                raise ValueError("FASTQ file is interleaved")
            else:
                raise ValueError("FASTQ file is not paired-end")
    
    @property
    def fastq(self):
        self._verify_1_fastq()
        return self._fq
    
    @property
    def fastq1(self):
        self._verify_2_fastqs()
        return self._fq
    
    @property
    def fastq2(self):
        self._verify_2_fastqs()
        return self._fq2
    
    @property
    def interleaved(self):
        return self.paired and self._fq2 is None
    
    @property
    def fastq_files(self) -> List[str]:
        files = [self._fq]
        if self._fq2 is not None:
            files.append(self._fq2)
        return files
    
    @property
    def outputs(self):
        return [self.to_temp_dir(fq) for fq in self.fastq_files]
    
    
    
    @classmethod
    def _sample_name(cls, fastq1: str, fastq2: Optional[str] = None):
        extensions = (".fastq", ".fq")
        if not any(fastq1.endswith(ext) for ext in extensions):
            raise ValueError(f"{fastq1} does not end with a FASTQ extension")
        name1 = os.path.basename(fastq1)
        while "." in name1 and not any(map(name1.endswith, extensions)):
            name1, _ = os.path.splitext(name1)
        name1, ext = os.path.splitext(name1)
        if fastq2 is not None:
            name2 = cls._sample_name(fastq2)
            if len(name1) != len(name2):
                raise ValueError("FASTQ files 1 and 2 names do not match")
            diff_pos = [pos for pos, (c1, c2) in enumerate(zip(name1, name2))
                        if c1 != c2]
            if len(diff_pos) != 1:
                raise ValueError("Names of FASTQ files 1 and 2 must differ at "
                                 "exactly 1 position")
            pos = diff_pos[0]
            if name1[pos] == "1" and name2[pos] == "2":
                seps = ("_", "-", "")
                keys = ("read", "r", "mate", "m", "pair", "p", "")
                for sk in itertools.product(seps, keys):
                    if ((pfx := "".join(sk)) and (start := pos - len(pfx)) >= 0
                            and (name1[start:pos].lower() == pfx)):
                        name = name1[:start] + name1[pos+1:]
                        return name
                name = name1[:pos] + name1[pos+1:]
                return name
            else:
                raise ValueError("FASTQs must be labeled '1' and '2'")
        else:
            return name1
    
    @property
    def sample_name(self):
        return self._sample_name(self._fq, self._fq2)
        
    def fastqc(self, extract: bool = DEFAULT_EXTRACT):
        cmd = [FASTQC_CMD]
        if extract:
            cmd.append("--extract")
        cmd.extend(self.fastq_files)
        run_cmd(cmd)


class FastqInterleaver(FastqBase):
    operation_dir = "align/interleave"

    def interleave(self):
        if self.interleaved:
            raise ValueError("FASTQ is already interleaved")
        ext = os.path.splitext(self.fastq1)[1].rstrip(".")
        output = self.to_temp_dir(f"{self.sample_name}.{ext}")
        cmd = [PASTE_CMD, self.fastq1, self.fastq2, ">", output]
        run_cmd(cmd)
        self._fq, self._fq2 = output, None


class FastqMasker(FastqBase):
    operation_dir = "align/mask"

    def _mask(self, input: str, output: str, min_qual: int):
        min_code = min_qual + self.encoding
        NL = b"\n"[0]
        BN = BASEN[0]
        with open(input, "rb") as fqi, open(output, "wb") as fqo:
            for seq_header in fqi:
                masked = bytearray(seq_header)
                bases = fqi.readline()
                qual_header = fqi.readline()
                quals = fqi.readline()
                if len(bases) != len(quals):
                    raise ValueError("seq and qual have different lengths")
                masked.extend(base if qual >= min_code or base == NL else BN
                              for base, qual in zip(bases, quals))
                masked.extend(qual_header)
                masked.extend(quals)
                fqo.write(masked)

    def mask(self, min_qual=DEFAULT_MIN_BASE_QUALITY, **kwargs):
        outputs = self.outputs
        for fq, out in zip(self.fastq_files, outputs):
            self._mask(fq, out, min_qual)
        self._fq, self._fq2 = outputs


class FastqTrimmer(FastqBase):
    operation_dir = "align/trim"

    def cutadapt(self,
                 qual1=DEFAULT_MIN_BASE_QUALITY,
                 qual2=None,
                 adapters15=(),
                 adapters13=(DEFAULT_ILLUMINA_ADAPTER,),
                 adapters25=(),
                 adapters23=(DEFAULT_ILLUMINA_ADAPTER,),
                 min_overlap=DEFAULT_MIN_OVERLAP,
                 max_error=DEFAULT_MAX_ERROR,
                 indels=DEFAULT_INDELS,
                 nextseq=DEFAULT_NEXTSEQ,
                 discard_trimmed=DEFAULT_DISCARD_TRIMMED,
                 discard_untrimmed=DEFAULT_DISCARD_UNTRIMMED,
                 min_length=DEFAULT_MIN_LENGTH,
                 cores=DEFAULT_TRIM_CORES,
                 **_):
        cmd = [CUTADAPT_CMD]
        if cores >= 0:
            cmd.append(f"--cores {cores}")
        if nextseq:
            nextseq_qual = qual1 if qual1 else DEFAULT_MIN_BASE_QUALITY
            cmd.append(f"--nextseq-trim {nextseq_qual}")
        else:
            if qual1 is not None:
                cmd.append(f"-q {qual1}")
            if qual2 is not None:
                self.fastq2
                cmd.append(f"-Q {qual2}")
        adapters = {"g": adapters15, "a": adapters13,
                    "G": adapters25, "A": adapters23}
        for arg, adapter in adapters.items():
            if adapter and (arg.islower() or self.paired):
                if isinstance(adapter, str):
                    adapter = (adapter,)
                if not isinstance(adapter, tuple):
                    raise ValueError("adapters must be str or tuple")
                for adapt in adapter:
                    cmd.append(f"-{arg} {adapt}")
        if min_overlap >= 0:
            cmd.append(f"-O {min_overlap}")
        if max_error >= 0:
            cmd.append(f"-e {max_error}")
        if not indels:
            cmd.append("--no-indels")
        if discard_trimmed:
            cmd.append("--discard-trimmed")
        if discard_untrimmed:
            cmd.append("--discard-untrimmed")
        if min_length:
            cmd.append(f"-m {min_length}")
        if self.interleaved:
            cmd.append("--interleaved")
        outputs = self.outputs
        cmd.append(f"-o {outputs[0]}")
        if outputs[1] is not None:
            self.fastq2
            cmd.append(f"-p {outputs[1]}")
        cmd.extend(self.fastq_files)
        run_cmd(cmd)
        self._fq, self._fq2 = outputs


class AlignmentBase(SequencingFileBase):
    __slots__ = ["_ref", "_xam"]

    def __init__(self, project_dir: str, ref_file: str, xam_prefix: str,
                 paired: bool = False, encoding: int = PHRED_ENCODING) -> None:
        super().__init__(project_dir, paired, encoding)
        self._ref = ref_file
        self._xam = xam_prefix
    
    @property
    def ref_file(self):
        return self._ref
    
    @property
    def xam_prefix(self):
        return self._xam
    
    @property
    def ref_prefix(self):
        return os.path.splitext(self.ref_file)
    
    @property
    def ref_filename(self):
        return os.path.splitext(os.path.basename(self.ref_file))[0]
    
    @property
    def sam_input(self):
        return f"{self.xam_prefix}.sam"
    
    @property
    def sam_temp(self):
        return self.to_temp_dir(self.sam_input)
    
    @property
    def bam_out(self):
        return self.to_output_dir(f"{self.xam_prefix}.bam")
    

class FastqAligner(FastqBase, AlignmentBase):
    operation_dir = "align/bowtie2"

    def __init__(self, project_dir: str, ref_file: str, fastq: str,
                 fastq2: Optional[str] = None, paired: bool = False,
                 encoding: int = PHRED_ENCODING) -> None:
        FastqBase.__init__(self, project_dir, fastq, fastq2, paired, encoding)
        AlignmentBase.__init__(self, project_dir, ref_file, self.sample_name,
                               self.paired, self.encoding)

    def bowtie2_build(self):
        """
        Build an index of a reference genome using Bowtie 2.
        :param ref: (str) path to the reference genome FASTA file
        :return: None
        """
        cmd = [BOWTIE2_BUILD_CMD, self.ref_file, self.ref_prefix]
        run_cmd(cmd)
    
    def bowtie2(self,
                local=DEFAULT_LOCAL,
                unaligned=DEFAULT_UNALIGNED,
                discordant=DEFAULT_DISCORDANT,
                mixed=DEFAULT_MIXED,
                dovetail=DEFAULT_DOVETAIL,
                contain=DEFAULT_CONTAIN,
                frag_len_min=DEFAULT_FRAG_LEN_MIN,
                frag_len_max=DEFAULT_FRAG_LEN_MAX,
                map_qual_min=DEFAULT_MAP_QUAL_MIN,
                n_ceil=DEFAULT_N_CEIL,
                seed=DEFAULT_SEED,
                extensions=DEFAULT_EXTENSIONS,
                reseed=DEFAULT_RESEED,
                padding=DEFAULT_PADDING,
                threads=DEFAULT_ALIGN_THREADS,
                metrics=DEFAULT_METRICS,
                **kwargs):
        cmd = [BOWTIE2_CMD]
        if self._fq2 is not None:
            cmd.extend(["-1", self.fastq1, "-2", self.fastq2])
        elif self.interleaved:
            cmd.extend(["--interleaved", self.fastq])
        else:
            cmd.extend(["-U", self.fastq])
        cmd.append(f"-x {self.ref_prefix}")
        cmd.append(f"-S {self.sam_temp}")
        cmd.append(f"{self.encoding_arg}")
        cmd.append("--xeq")
        cmd.append(f"--ma {MATCH_BONUS}")
        cmd.append(f"--mp {MISMATCH_PENALTY}")
        cmd.append(f"--np {N_PENALTY}")
        cmd.append(f"--rfg {REF_GAP_PENALTY}")
        cmd.append(f"--rdg {READ_GAP_PENALTY}")
        if local:
            cmd.append("--local")
        if not unaligned:
            cmd.append("--no-unal")
        if not discordant:
            cmd.append("--no-discordant")
        if not mixed:
            cmd.append("--no-mixed")
        if dovetail:
            cmd.append("--dovetail")
        if not contain:
            cmd.append("--no-contain")
        if frag_len_min:
            cmd.append(f"-I {frag_len_min}")
        if frag_len_max:
            cmd.append(f"-X {frag_len_max}")
        if map_qual_min:
            cmd.append(f"--score-min C,{map_qual_min}")
        if n_ceil:
            cmd.append(f"--n-ceil {n_ceil}")
        if seed:
            cmd.append(f"-L {seed}")
        if extensions:
            cmd.append(f"-D {extensions}")
        if reseed:
            cmd.append(f"-R {reseed}")
        if padding:
            cmd.append(f"--dpad {padding}")
        if threads:
            cmd.append(f"-p {threads}")
        if metrics:
            cmd.append(f"--met-stderr --met {metrics}")
        if IGNORE_QUALS:
            cmd.append("--ignore-quals")
        run_cmd(cmd)


class AlignmentCleaner(AlignmentBase):
    operation_dir = "align/cleaned"

    def remove_equal_mappers(self):
        print("\n\nRemoving reads mapping equally to multiple locations")
        pattern_a = re.compile(SAM_ALIGN_SCORE + rb"(\d+)")
        pattern_x = re.compile(SAM_EXTRA_SCORE + rb"(\d+)")

        def get_score(line, ptn):
            return (float(match.groups()[0])
                    if (match := ptn.search(line)) else None)

        def is_best_alignment(line):
            return ((score_x := get_score(line, pattern_x)) is None
                    or score_x < get_score(line, pattern_a))

        kept = 0
        removed = 0
        with open(self.sam_input, "rb") as sami, open(self.sam_temp, "wb") as samo:
            # Copy the header from the input to the output SAM file.
            while (line := sami.readline()).startswith(SAM_HEADER):
                samo.write(line)
            if self.paired:
                for line2 in sami:
                    if is_best_alignment(line) or is_best_alignment(line2):
                        samo.write(line)
                        samo.write(line2)
                        kept += 1
                    else:
                        removed += 1
                    line = sami.readline()
            else:
                while line:
                    if is_best_alignment(line):
                        samo.write(line)
                        kept += 1
                    else:
                        removed += 1
                    line = sami.readline()
        total = kept + removed
        items = "Pairs" if self.paired else "Reads"
        print(f"\n{items} processed: {total}")
        print(f"{items} kept: {kept} ({round(100 * kept / total, 2)}%)")
        print(f"{items} lost: {removed} ({round(100 * removed / total, 2)}%)")
        return kept, removed


class AlignmentFinisher(AlignmentBase):
    operation_dir = "align"

    def sort(self):
        cmd = [SAMTOOLS_CMD, "sort", "-o", self.bam_out, self.sam_input]
        run_cmd(cmd)
    
    def index(self):
        cmd = [SAMTOOLS_CMD, "index", "-b", self.bam_out]
        run_cmd(cmd)


def run(project_dir, ref, fastq1, fastq2=None, **kwargs):
    # Check the file extensions.
    primer1 = "CAGCACTCAGAGCTAATACGACTCACTATA"
    primer1rc = "TATAGTGAGTCGTATTAGCTCTGAGTGCTG"
    primer2 = "TGAAGAGCTGGAACGCTTCACTGA"
    primer2rc = "TCAGTGAAGCGTTCCAGCTCTTCA"
    adapters5 = (primer1, primer2rc)
    adapters3 = (primer2, primer1rc)
    primer_trimmed_reads = os.path.join(output_dir,
        f"__{sample}_primer_trimmed.fastq")
    trim(adapter_trimmed_reads, primer_trimmed_reads, interleaved=paired,
         adapters15=adapters5, adapters13=adapters3,
         adapters25=adapters5, adapters23=adapters3,
         min_overlap=6, min_length=10, discard_trimmed=True)
    try_remove(adapter_trimmed_reads)
    # Mask low-quality bases remaining in the trimmed file.
    masked_trimmed_reads = os.path.join(output_dir,
        f"__{sample}_masked_trimmed.fastq")
    mask_low_qual(primer_trimmed_reads, masked_trimmed_reads)
    try_remove(primer_trimmed_reads)
    # Quality check the trimmed FASTQ file.
    #fastqc(output_dir, masked_trimmed_reads)
    # Index the reference.
    prefix = index(ref)
    # Align the reads to the reference.
    sam_align = os.path.join(output_dir, f"__{sample}_align.sam")
    bowtie(sam_align, prefix, masked_trimmed_reads, interleaved=True)
    try_remove(masked_trimmed_reads)
    # Delete reads aligning equally well to multiple locations.
    sam_pruned = os.path.join(output_dir, f"__{sample}_pruned.sam")
    remove_equal_mappers(sam_align, sam_pruned)
    # Delete the non-pruned SAM file.
    try_remove(sam_align)
    # Sort the SAM file while converting to BAM format
    bam_file = os.path.join(output_dir, f"{sample}.bam")
    sort_sam(sam_pruned, bam_file)
    # Delete the SAM file.
    try_remove(sam_pruned)
    # Index the BAM file.
    index_bam(bam_file)
