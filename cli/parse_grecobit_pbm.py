
import argparse
import pandas as pd
from pathlib import Path
import sys 
import shutil

sys.path.append("/home_local/dpenzar/bibis_git/ibis-challenge")
from bibis.pbm.config import PBMConfig

LEADERBOARD_EXCEL = "/home_local/dpenzar/IBIS TF Selection - Nov 2022 _ Feb 2023.xlsx"
SPLIT_SHEET_NAME = "v3 TrainTest marked (2023)"
PBM_DIR = Path("/home_local/vorontsovie/greco-data/release_8d.2022-07-31/full/")

EXPTP2SPLIT = {"PBM.ME": "Train",
               "PBM.HK": "Val"}
STAGES = ('Final', 'Leaderboard')

OUT_DIR = Path("/home_local/dpenzar/BENCH_FULL_DATA/PBM")



parser = argparse.ArgumentParser()
parser.add_argument("--neg2pos_ratio",
                    type=int, 
                    default=10)
args = parser.parse_args()

ibis_table = pd.read_excel(LEADERBOARD_EXCEL, sheet_name=SPLIT_SHEET_NAME)
ibis_table = ibis_table[['Transcription factor', 'PBM', 'PBM.1', 'Stage']]
ibis_table.columns = ['tf', 'replics', 'split', 'stage']
ibis_table['replics'] = ibis_table['replics'].str.split(',')

from collections import defaultdict


if not ibis_table['stage'].isin(STAGES).all():
    raise Exception(f"Some tfs has invalid stage: {ibis_table[~(ibis_table['stage'].isin(STAGES))]}")

for stage in STAGES:
    copy_paths = defaultdict(lambda : {"train": {"QNZS": [], "SD": []}, 
                                   "test": {"QNZS": [], "SD": []}})
    stage_ibis_table =  ibis_table[ibis_table['stage'] == stage]
    
    for ind, tf, reps, ibis_split in stage_ibis_table[['tf', 'replics', 'split'] ].itertuples():
        if ibis_split == "-":
            continue
        if isinstance(reps, float): # skip tf without pbms
            print(f"Skipping factor tf: {tf}. Its split ({ibis_split}) is not none but there is no experiments for that factor", file=sys.stderr)
            continue
        for rep in reps:
            for norm in ["QNZS", "SD"]:
                norm_dir = PBM_DIR / f"PBM.{norm}" 
                for exp_type, split in EXPTP2SPLIT.items():
                    split_dir = norm_dir / f"{split}_intensities"

                    for path in split_dir.glob(f"*{exp_type}@{rep}*"):
                            if split == "Train":
                                real_split = "train"
                            elif split == "Val":
                                real_split = "test"
                            else:
                                raise Exception(f"Wrong split {split}")
                            
                            if real_split == "train" and ibis_split == "Test":
                                print(f"Skipping file {path} for {tf} as it is from wrong split", file=sys.stderr)
                                continue
                            if real_split == "test" and ibis_split == "Train":
                                print(f"Skipping file {path} for {tf} as it is from wrong split", file=sys.stderr)
                                continue
                            name = path.name
                            exp_type = exp_type.replace("PBM.", "")
                            copy_paths[tf][real_split][norm].append(path)
        for sp in ibis_split.split("/"):
            if sp == "Train":
                if len(copy_paths[tf]['train']) == 0:
                    raise Exception(f"No train experiments for tf {tf} although train split is specified")
            elif sp == "Test":
                if len(copy_paths[tf]['test']) == 0:
                    raise Exception(f"No train experiments for tf {tf} although test split is specified")
            else:    
                raise Exception(f"Wrong split {sp}")

    configs_dir = OUT_DIR / "configs" / stage
    configs_dir.mkdir(exist_ok=True, parents=True)
    
    for tf, split_dt in copy_paths.items():
        cfg = PBMConfig(tf, 
                        train_paths=[],
                        test_paths=[],
                        protocol="ibis", 
                        neg2pos_ratio=args.neg2pos_ratio)
        for split, norm_dt in split_dt.items():
            split = split.lower()
            for norm, in_paths in norm_dt.items():            
                for ind, in_p in enumerate(in_paths, 1):
                    out_dir = OUT_DIR / tf / split / norm / exp_type
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"replic_{ind}.tsv"
                    shutil.copy(in_p, out_path)
                    if split == "train":
                        cfg.train_paths.append(str(out_path))
                    elif split == "test":
                        cfg.test_paths.append(str(out_path))
                    else:
                        raise Exception(f"Wrong split: {split}")
        cfg_path = configs_dir /  f"{tf}.json"
        cfg.save(cfg_path)