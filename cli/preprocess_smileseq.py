from pathlib import Path
import sys 
from collections import Counter 
import gzip
import tqdm
from Bio import SeqIO
import json
import argparse
import math
import random 

sys.path.append("/home_local/dpenzar/bibis_git/ibis-challenge")

from bibis.sms.config import RAW_SMSConfig
from bibis.sms.dataset import SMSRawDataset
from bibis.utils import merge_fastqgz
TEST_SEQ_LENGTH = 40
RAW_DIR =  Path("/home_local/dpenzar/BENCH_FULL_DATA/SMS/RAW/")
STAGES = ('Leaderboard', 'Final')
ZERO_DIR = Path("/mnt/space/depla/INPUT_libs")

OUT_DIR = Path("/home_local/dpenzar/BENCH_FULL_DATA/SMS/")
OUT_DIR.mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--recalc_unique", action="store_true")
args = parser.parse_args()


zero_seq_path = OUT_DIR / "zeros.json"
if zero_seq_path.exists() and not args.recalc_unique:
    print("Loading zero seqs")
    with open(zero_seq_path, "r") as inp:
        zero_seqs = set(json.load(inp))
else:
    zero_seqs_cnt = Counter()
    print("Deducing zero seqs")
    for zero_path in tqdm.tqdm(ZERO_DIR.glob("*.fastq")):
        with open(zero_path, "rt") as inp:
            seqs = (str(rec.seq).upper() for rec in SeqIO.parse(inp, format="fastq"))
            zero_seqs_cnt.update(seqs)
    zero_seqs = set(zero_seqs_cnt.keys())
    zero_seqs = {s for s in zero_seqs if len(s) == TEST_SEQ_LENGTH}
    with open(zero_seq_path, "w") as out:
        json.dump(list(zero_seqs), out)

total_stage_seqs = {}
for stage in STAGES:
    print(f"Stage {stage}")
    data_out_stage_dir = OUT_DIR /  "data" / stage
    data_out_stage_dir.mkdir(parents=True, exist_ok=True)
    unique_path = data_out_stage_dir / "unique.json"
    configs_dir = RAW_DIR / "configs" / stage
    if unique_path.exists() and not args.recalc_unique:
        print("Loading unique seqs")
        with open(unique_path, "r") as inp:
            unique_seqs = set(json.load(inp))
    else:
        print("Deducing unique seqs")
        seq_counter = Counter()
        
        for cfg_path in tqdm.tqdm(configs_dir.glob("*.json")):
            cfg = RAW_SMSConfig.load(cfg_path)
            for ds in cfg.datasets:
                with gzip.open(ds.path, "rt") as inp:
                    seqs = [str(rec.seq).upper() for rec in SeqIO.parse(inp, format="fastq")]
                    seq_counter.update(seqs)

        unique_seqs = set(seq for seq, cnt in seq_counter.items() if cnt == 1)
        unique_seqs = unique_seqs - zero_seqs
        with open(unique_path, "w") as out:
            json.dump(list(unique_seqs), out)
    total_stage_seqs[stage] = len(unique_seqs) 

    configs_out_stage_dir = OUT_DIR /  "configs" / stage
    configs_out_stage_dir.mkdir(exist_ok=True, parents=True)
    print("Writing filtered datases")
    unique_seqs_with_flanks = {}
    for cfg_path in tqdm.tqdm(configs_dir.glob("*.json")):
        cfg = RAW_SMSConfig.load(cfg_path)
        tf_out_dir = data_out_stage_dir / cfg.tf_name 
        tf_out_dir.mkdir(exist_ok=True, parents=True)
        uniq_datasets = []
        for ds in cfg.datasets:
            with gzip.open(ds.path, "rt") as inp:
                recs = [rec for rec in SeqIO.parse(inp, format="fastq")]
                recs = [rec for rec in recs if str(rec.seq).upper() in unique_seqs]
            unique_ds_path = tf_out_dir / Path(ds.path).name
            with gzip.open(unique_ds_path, "wt") as out:
                 SeqIO.write(recs, out, 'fastq')

            for rec in recs:
                seq = str(rec.seq).upper()
                unique_seqs_with_flanks[seq] = (ds.left_flank, ds.right_flank)

            unique_ds = SMSRawDataset(path=str(unique_ds_path),
                                      left_flank=ds.left_flank,
                                      right_flank=ds.right_flank)
            uniq_datasets.append(unique_ds)
        uniq_cfg = RAW_SMSConfig(tf_name=cfg.tf_name,
                                 split=cfg.split,
                                 datasets=uniq_datasets)
        out_cfg_path = configs_out_stage_dir / f"{uniq_cfg.tf_name}.json"
        uniq_cfg.save(out_cfg_path)
    
    flanked_seq_path = data_out_stage_dir / "unique_with_flanks.json"

    unique_seqs_with_flanks = {seq: flanks for seq, flanks in unique_seqs_with_flanks.items() \
                                   if len(seq) == TEST_SEQ_LENGTH}
    with open(flanked_seq_path, "w") as out:
        json.dump(unique_seqs_with_flanks, out, indent=4)

total_seqs = sum(total_stage_seqs.values())

inds = list(range(0, len(zero_seqs)))
random.shuffle(inds)
leader_end = math.ceil(len(zero_seqs) * total_stage_seqs['Leaderboard'] / total_seqs)
zero_seqs = list(zero_seqs)

leader_zeros = [zero_seqs[i] for i in inds[:leader_end]]
print(len(leader_zeros))
data_out_stage_dir = OUT_DIR /  "data" / "Leaderboard"
with open(data_out_stage_dir / "zeros.json", "w") as out:
    json.dump(leader_zeros, out)

final_zeros = [zero_seqs[i] for i in inds[leader_end:]]
print(len(final_zeros))
data_out_stage_dir = OUT_DIR /  "data" / "Final"
with open(data_out_stage_dir / "zeros.json", "w") as out:
    json.dump(final_zeros, out)