import concurrent.futures

import pandas as pd
import numpy as np 

from labels import BinaryLabel
from pwmeval import PWMEvalPFMPredictor, PWMEvalPWMPredictor
from prediction import Prediction
from dataset import Dataset, DatasetType
from pathlib import Path
from attr import field, define
from enum import Enum 
from typing import ClassVar, Optional, Union
from scorer import Scorer
from exceptions import BenchmarkException, WrongBecnhmarkModeException
from utils import register_enum
from typing import List
from collections.abc import Sequence
from pathlib import Path
from model import DictPredictor, Model 
from traceback import print_exc

@define
class ModelEntry:
    name: str 
    model: Model

@register_enum
class BenchmarkMode(Enum):
    USER = 1
    ADMIN = 2

@define
class Benchmark:
    name: str
    datasets: Sequence[Dataset]
    scorers: Sequence[Scorer]
    results_dir: Path
    metainfo: dict
    pwmeval_path: Optional[Path] = None
    models: List[ModelEntry] = field(factory=list)

    SKIPVALUE: ClassVar[float] = np.nan

    def write_datasets(self, mode: BenchmarkMode):
        if mode is BenchmarkMode.USER:
            self.write_datasets_for_user()
        elif mode is BenchmarkMode.ADMIN:
            self.write_datasets_for_admin()
        else:
            raise WrongBecnhmarkModeException()
        raise NotImplementedError()

    def write_datasets_for_user(self, path: Optional[Path]=None):
        if path is None:
            path = Path.cwd()
        path.mkdir(exist_ok=True)
        for ds in self.datasets:
            if ds.type is DatasetType.TRAIN:
                pass

        raise NotImplementedError()

    def write_datasets_for_admin(self):
        raise NotImplementedError()

    def write_ideal_model(self, path: Path):
        '''
        writes real labels for both train and test set
        in the prediction file format
        '''
        with path.open("w") as out:
            for ds in self.datasets:
                for entry in ds:
                    print(entry.tag, entry.label.value, sep="\t", file=out)  # type: ignore
    
    def add_pfm(self, 
                pref: str, 
                pfm_path: Union[Path, str], 
                pwmeval_path: Optional[Path]=None):
        if pwmeval_path is None:
            if self.pwmeval_path is None:
                raise BenchmarkException("Can't add PWM due to unspecified pwmeval_path")
            pwmeval_path = self.pwmeval_path
        if isinstance(pfm_path, str):
            pfm_path = Path(pfm_path)
        model = PWMEvalPFMPredictor.from_pfm(pfm_path, pwmeval_path)
        self.add_model(f"{pref}_sumscore", model)
        model = PWMEvalPWMPredictor.from_pfm(pfm_path, pwmeval_path)
        self.add_model(f"{pref}_best", model)

    def add_model(self, name: str, model: Model):
        entry = ModelEntry(name, model)
        self.models.append(entry)

    def add_prediction(self, name: str, pred: Prediction):
        model = DictPredictor(pred)
        entry = ModelEntry(name, model)
        self.models.append(entry)

    def score(self, labels: List[BinaryLabel], scores: List[float]) -> dict[str, float]:
        ds_scores = {}
        for sc in self.scorers:
            score = sc.score(y_real=labels, y_score=scores)
            ds_scores[sc.name] = score
        return ds_scores

    @property
    def skipped_prediction(self) -> dict[str, float]:
        ds_scores = {sc.name: self.SKIPVALUE for sc in self.scorers}
        return ds_scores

    def score_model_on_ds(self,
                          model: Union[Model, ModelEntry], 
                          ds: Dataset) -> dict[str, float]:
        if len(ds) == 0:
            print(f"Size of {ds.name} is 0. Skipping dataset")
            return self.skipped_prediction

        if isinstance(model, ModelEntry):
            pred = model.model.score(ds)
        else:
            pred = model.score(ds)

        scores, labels = [], []
        skip_ds=False
        for e in ds:
            try:
                scores.append(pred[e.tag])
            except KeyError:
                if isinstance(model, ModelEntry):
                    print(f"Model {model.name} returned no prediction for entry {e.tag} from {ds.name}. Skipping dataset")
                else:
                    print(f"Model returned no prediction for entry {e.tag} from {ds.name}. Skipping dataset")
                skip_ds = True
                break 
            labels.append(e.label)
        if skip_ds:
            return self.skipped_prediction
        
        ds_scores = self.score(labels, scores)
        return ds_scores

    def score_model(self, model: Union[Model, ModelEntry]) -> dict[str, dict[str, float]]:
        model_scores = {}
        for ds in self.datasets:
            ds_scores = self.score_model_on_ds(model, ds)
            model_scores[ds.name] = ds_scores
        return model_scores

    def score_prediction(self, prediction: Prediction) -> dict[str, dict[str, float]]:
        model = DictPredictor(prediction)
        return self.score_model(model)

    def get_results_file_path(self, name: str):
        return self.results_dir / f"{name}.tsv"
    
    def run(self, n_procs=1, timeout=None):
        self.results_dir.mkdir(exist_ok=True)
        if n_procs == 1:
            results = self.run_single()
        else:
            print("Parallel run")
            results = self.run_parallel(n_procs=n_procs, timeout=timeout)

        for name, scores in results.items():
            path = self.get_results_file_path(name)
            df = pd.DataFrame(scores)
            df.to_csv(path, sep="\t")

    def run_single(self):
        return {entry.name: self.score_model(entry.model) for entry in self.models}
    
    def run_parallel(self, n_procs=2, timeout=None) -> dict[str, dict[str, dict[str, float]]]:
        self.results_dir.mkdir(exist_ok=True)
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=n_procs)
        futures = {}
        for model in self.models:
            for ds in self.datasets:
                tag = (model.name, ds.name)
                ft = executor.submit(self.score_model_on_ds, model, ds)
                futures[ft] = tag
        concurrent.futures.wait(futures, timeout)
 
        results = {m.name: {} for m in self.models}
        for ft in futures:
            m_name, ds_name = futures[ft]
            try:
                scores = ft.result()
            except Exception as exc:
                print("Exception occured while running model {m_name} on dataset {ds_name}")
                print_exc()
                scores = self.skipped_prediction
            results[m_name][ds_name] = scores

        return results