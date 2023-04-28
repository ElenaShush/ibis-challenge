import argparse

import glob
import json
import sys

import numpy as np

from pathlib import Path

parser = argparse.ArgumentParser()

parser.add_argument("--benchmark_root", 
                    type=str,
                    required=True)
parser.add_argument("--benchmark_name", 
                    type=str,
                    required=True)
parser.add_argument("--benchmark_kind", 
                    type=str,
                    required=True)
parser.add_argument("--scorers", 
                    type=str,
                    required=True)
parser.add_argument("--out_dir",
                    type=str,
                    required=True)
parser.add_argument("--pwmeval",
                    type=str,
                    default="/home_local/dpenzar/PWMEval/pwm_scoring")
parser.add_argument("--bibis_root",
                    default="/home_local/dpenzar/bibis_git/ibis-challenge",
                    type=str)
args = parser.parse_args()

sys.path.append(args.bibis_root)

from bibis.benchmark.benchmarkconfig import BenchmarkConfig
from bibis.benchmark.dataset import DatasetInfo, entries2tsv, seqentry2interval_key
from bibis.scoring.scorer import ScorerInfo
from bibis.benchmark.score_submission import ScoreSubmission
from bibis.benchmark.pwm_submission import PWMSubmission
from bibis.seq.seqentry import SeqEntry, read_fasta, write_fasta

benchmark = Path(args.benchmark_root)

ds_cfg_paths = benchmark / "valid" / "*" / "answer" / "*" / "config.json"

config_paths = glob.glob(str(ds_cfg_paths))

with open(args.scorers, "r") as out:
    scorers_dt = json.load(out)

cfg = BenchmarkConfig(
    name=args.benchmark_name,
    kind=args.benchmark_kind,
    datasets=[DatasetInfo.load(p) for p in config_paths],
    scorers=[ScorerInfo.from_dict(sc) for sc in scorers_dt],
    pwmeval_path=args.pwmeval,
    metainfo={}    
)


out_dir = Path(args.out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

cfg_path = out_dir / f"benchmark.json"
cfg.save(cfg_path)

# collect tags 
tags = {}
answers = {}
tfs = set()

for ds in cfg.datasets:
    tfs.add(ds.tf)
    ans = ds.answer()
    for tag, label in ans.items():
        tags[tag] = label
        answers[(ds.tf, tag)] = label

score_template = ScoreSubmission.template(tag_col_name="peaks",
                                          tf_names=list(tfs),
                                          tags=list(tags.keys()))
aaa_template_path = out_dir / "aaa_template.tsv"
score_template.write(aaa_template_path)

for tf in score_template.tf_names:
    for tag in score_template.tags:
        score_template[tf][tag] = np.random.random()
random_aaa_path = out_dir / "aaa_random.tsv"
score_template.write(random_aaa_path)

for tf in score_template.tf_names:
    for tag in score_template.tags:
        score_template[tf][tag] = answers.get((tf, tag), 0)

ideal_aaa_path = out_dir / "aaa_ideal.tsv"
score_template.write(ideal_aaa_path)    

pwm_submission_path = out_dir / "pwm_submission.txt"
with open(pwm_submission_path, "w") as out:
    for ind, tf in enumerate(tfs):
        for i in range(PWMSubmission.MAX_PWM_PER_TF):
            tag = f"{tf}_motif{i+1}"
            print(f">{tf} {tag}", file=out)
            for i in range(np.random.randint(3, 11)):
                a, t, g, c = np.random.dirichlet([1,1,1,1])
                p = PWMSubmission.MAX_PRECISION
                print(f"{a:.0{p}f} {t:.0{p}f} {g:.0{p}f} {c:.0{p}f}", file=out)
            print(file=out)
            
sub_fasta_paths = glob.glob(str(benchmark / "valid" / "*" / "participants" / "*.fasta"))
unique_entries: dict[str, SeqEntry] = {}
for path in sub_fasta_paths:
    entries = read_fasta(path)
    for e in entries:
        unique_entries[e.tag] = e
        
final_entries = list(unique_entries.values())
final_entries.sort(key=seqentry2interval_key)

participants_fasta_path = out_dir / "participants.fasta"
write_fasta(entries=final_entries, 
            handle=participants_fasta_path)
participants_tsv_path = out_dir / "participants.bed"
entries2tsv(entries=final_entries, 
            path=participants_tsv_path)

